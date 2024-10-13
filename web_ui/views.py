from .models import UserAccess
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.template import loader
from django.utils.encoding import smart_str
from django.contrib.auth import logout
from django.http import StreamingHttpResponse, FileResponse
from django.contrib.auth import get_user_model
import mimetypes
from wsgiref.util import FileWrapper
import pathlib
from io import BytesIO
import tarfile
import glob
import json
import os


srcs = '/nas' if os.path.exists('/nas') else '/home/palm/'
max_locked_depth = 1

class FileStream:
    def __init__(self):
        self.buffer = BytesIO()
        self.offset = 0

    def write(self, s):
        self.buffer.write(s)
        self.offset += len(s)

    def tell(self):
        return self.offset

    def close(self):
        self.buffer.close()

    def pop(self):
        s = self.buffer.getvalue()
        self.buffer.close()
        self.buffer = BytesIO()
        return s

    @classmethod
    def yield_tar(cls, file_data_iterable, removed_index):
        stream = FileStream()
        tar = tarfile.TarFile.open(mode='w|', fileobj=stream, bufsize=tarfile.BLOCKSIZE)
        for file in file_data_iterable:
            if file.is_file():
                file_name = str(file.absolute())[removed_index:]
                file_size = file.lstat().st_size
                file_date = file.lstat().st_mtime
                file_path = file.absolute()

                tar_info = tarfile.TarInfo(file_name)
                tar_info.size = int(file_size)
                tar_info.mtime = file_date
                tar.addfile(tar_info)
                yield stream.pop()

                with open(file_path, 'rb') as file_data:
                    while True:
                        data = file_data.read(tarfile.BLOCKSIZE)
                        if not data:
                            break
                        tar.fileobj.write(data)
                        yield stream.pop()

                blocks, remainder = divmod(tar_info.size, tarfile.BLOCKSIZE)
                if remainder > 0:
                    tar.fileobj.write(tarfile.NUL * (tarfile.BLOCKSIZE - remainder))
                    yield stream.pop()
                    blocks += 1
                tar.offset += blocks * tarfile.BLOCKSIZE
            else:
                tar_info = tarfile.TarInfo(str(file.absolute())[removed_index:])
                tar_info.type = b'5'
                tar.addfile(tar_info)

        tar.close()
        yield stream.pop()


def get_context(request):
    context = {
        'username': request.user,
        'is_staff': request.user.is_staff,
    }

    return context


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{int(num)} {unit}{suffix}"
        num /= 1024.0
    return f"{int(num)} Yi{suffix}"


def download_single_file(path):
    filename = os.path.basename(path)
    chunk_size = 8192
    response = StreamingHttpResponse(
        FileWrapper(
            open(path, "rb"),
            chunk_size,
        ),
        content_type=mimetypes.guess_type(path)[0],
    )
    response["Content-Length"] = os.path.getsize(path)
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def download_directory(path):
    files = [p for p in sorted(pathlib.Path(srcs).rglob(f'{path}**/*'))]

    response = FileResponse(
        FileStream.yield_tar(files, len(srcs)),
        content_type="application/x-tar"
    )
    response["Content-Disposition"] = f'attachment; filename="{pathlib.Path(path).name}.tar"'
    return response


def get_navigator(path, prefix='files'):
    # <a href="{{ current_path }}">{{ current_path }}</a>
    nav = f'<a href="/{prefix}/" class="h1" rel="keep-params">HOME</a>/'
    chunks = path.split('/')
    for i, chunk in enumerate(chunks):
        if chunk == '':
            continue
        href = os.path.join(*chunks[:i+1])
        nav += f'<a href="/{prefix}/{href}" class="h1" rel="keep-params">{chunk}</a>/'
    return nav


@login_required(redirect_field_name=None)
def download(request, path=''):
    return download_directory(path)


def user_can_read(path, context):
    paths = '/'.join(path.split('/')[:max_locked_depth])
    path = path.split('/')[max_locked_depth]
    if not paths.endswith('/'):
        paths += '/'
    useraccess = UserAccess.objects.filter(username=context['username'], path=paths)
    if len(useraccess) == 0:
        return False
    return path in useraccess[0].reads


def get_table(context, path, username):
    files = []
    dirs = []
    useraccess = UserAccess.objects.filter(username=username, path=path)
    reads = []
    writes = []
    if len(useraccess) > 0:
        reads = useraccess[0].reads
        writes = useraccess[0].writes
    for file in sorted(os.listdir(os.path.join(srcs, path))):
        read = False
        write = False
        if len(dirs) + len(files) > 100:
            context['redacted'] = True
            break
        if os.path.isdir(os.path.join(srcs, path, file)):
            # dirs.append(os.path.join(path, file) + '/')
            try:
                num = len(os.listdir(os.path.join(srcs, path, file)))
            except:
                continue
            download = os.path.join('/download', path, file)
            if file in reads:
                read = True
            if file in writes:
                write = True
            if context['is_staff'] or read or (len(path.split('/')) > max_locked_depth+1 and user_can_read(path, context)):
                dirs.append({'path': file, 'num': num, 'download': download, 'read': read, 'write': write})
        else:
            # files.append(os.path.join(path, file))
            p = pathlib.Path(os.path.join(srcs, path, file))
            if file in reads:
                read = True
            if file in writes:
                write = True
            if context['is_staff'] or read or (len(path.split('/')) > max_locked_depth+1 and user_can_read(path, context)):
                files.append({'path': file, 'size': sizeof_fmt(p.lstat().st_size), 'download': file, 'read': read, 'write': write})
    return files, dirs


@login_required(redirect_field_name=None)
def files(request, path=''):
    template = loader.get_template("files.html")
    if not os.path.isdir(os.path.join(srcs, path)):
        if path.endswith('/'):
            path = path[:-1]
        return download_single_file(os.path.join(srcs, path))
    
    context = get_context(request)
    context['navigator'] = get_navigator(path)
    files, dirs = get_table(context, path, context['username'])
    context['directories'] = dirs
    context['files'] = files

    return HttpResponse(template.render(context, request))


def logout_view(request):
    logout(request)
    return files(request)


@login_required(redirect_field_name=None)
def permission(request):
    template = loader.get_template("permission_select.html")
    User = get_user_model()
    users = User.objects.all()
    context = get_context(request)
    context['users'] = users
    return HttpResponse(template.render(context, request))


@login_required(redirect_field_name=None)
@user_passes_test(lambda u: u.is_superuser)
def permission_view(request, path=''):
    if not request.GET.get("user"):
        return permission(request)
    if request.method == "POST":
        reads = []
        writes = []
        for key in request.POST:
            if key.startswith('write') and request.POST[key] == 'on':
                writes.append(key[6:])
            if key.startswith('read') and request.POST[key] == 'on':
                reads.append(key[5:])
        useraccess = UserAccess.objects.filter(username=request.GET.get("user"), path=path)
        if len(useraccess) > 0:
            useraccess.update(
                reads=reads,
                writes=writes,
            )
        else:
            useraccess = UserAccess(
                username=request.GET.get("user"),
                path=path,
                reads=reads,
                writes=writes,
            )
            useraccess.save()
        return HttpResponse(b'success')

    else:
        template = loader.get_template("permissions.html")
        context = get_context(request)
        context['navigator'] = get_navigator(path, 'permission')
        files, dirs = get_table(context, path, request.GET.get("user"))
        context['directories'] = dirs
        context['files'] = files

        return HttpResponse(template.render(context, request))
