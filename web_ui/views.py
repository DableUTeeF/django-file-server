from .forms import UploadFileForm
from .models import UserAccess, DownloadToken
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404, JsonResponse, HttpResponseRedirect
from django.template import loader
from django.utils.encoding import smart_str
from django.contrib.auth import logout
from django.http import StreamingHttpResponse, FileResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
import mimetypes
from wsgiref.util import FileWrapper
import pathlib
from io import BytesIO
import tarfile
import uuid
import os

readonly = os.environ.get('READ_ONLY', False)
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
                tar_info.mode = 0o744
                tar.addfile(tar_info)

        tar.close()
        yield stream.pop()


def get_context(request):
    context = {
        'username': request.user,
        'is_staff': request.user.is_staff,
        'readonly': readonly
    }

    return context


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{int(num)} {unit}{suffix}"
        num /= 1024.0
    return f"{int(num)} Yi{suffix}"


def download_single_file(path):
    path = os.path.join(srcs, path)
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
    response['Accept-Ranges'] = 'bytes'
    return response


def download_directory(path):
    downloadpath = pathlib.Path(os.path.join(srcs, path))
    files = [p for p in sorted(downloadpath.rglob(f'*'))]
    sizes = [p.lstat().st_size for p in files if p.is_file()]

    response = FileResponse(
        FileStream.yield_tar(files, len(str(downloadpath.absolute())) - len(downloadpath.name)),
        content_type="application/x-tar"
    )
    response["Content-Length"] = sum(sizes)
    response["Content-Disposition"] = f'attachment; filename="{pathlib.Path(path).name}.tar"'
    response['Accept-Ranges'] = 'bytes'
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


# @login_required(redirect_field_name=None)
def download(request, path=''):
    if not request.user.is_authenticated:
        if request.GET.get('next') is not None:
            if 'logout' in request.GET.get('next'):
                return HttpResponseRedirect('/login')
        return HttpResponseRedirect(f'/login?next=/directories/{path}')
    return download_directory(path)

def hash_download(request, hash):
    if hash.endswith('/'):
        hash = hash[:-1]
    tokens = DownloadToken.objects.filter(uuid=hash)
    if len(tokens) == 0:
        raise Http404
    if (timezone.now() - tokens[0].timestamp).days > 7:
        raise Http404
    if os.path.isdir(os.path.join(srcs, tokens[0].path)):
        return download_directory(tokens[0].path)
    else:
        return download_single_file(tokens[0].path)

@login_required(redirect_field_name=None)
def gethash(request):
    """
        pathname: window.location.pathname,
        name: name
    """
    if request.method == "POST":
        context = get_context(request)
        hash = uuid.uuid4().hex
        pathname = os.path.join(
            request.POST['pathname'][7:],
            request.POST['name'][5:]
        )
        tokens = DownloadToken(
            username=context['username'],
            path=pathname,
            timestamp=timezone.now(),
            uuid=hash,
        )
        tokens.save()
        return JsonResponse({'hash': request.build_absolute_uri('/download/'+hash)})
    return HttpResponse(status=405)


def user_can_read_write(path, name, username):
    useraccess = UserAccess.objects.filter(username=username, directory=path, name=name)
    if len(useraccess) == 0:
        return False, False
    return useraccess[0].reads, useraccess[0].writes


def get_table(context, path, username):
    read = context['is_staff']
    dirpath = path
    while True and not context['is_staff']:
        dirpath, subpath = os.path.split(dirpath)
        useraccess = UserAccess.objects.filter(username=username, directory=dirpath + '/', name=subpath)
        if len(useraccess) > 0:
            read = useraccess[0].reads
            break
        if len(dirpath) == 0:
            break
    if not read:
        return [], [], False
    files = []
    dirs = []
    for file in sorted(os.listdir(os.path.join(srcs, path)), key=str.casefold):
        if len(dirs) + len(files) > 200 and len(path.split('/')) > max_locked_depth:
            context['redacted'] = True
            break
        read, write = user_can_read_write(path, file, username)
        if os.path.isdir(os.path.join(srcs, path, file)):
            # dirs.append(os.path.join(path, file) + '/')
            try:
                num = len(os.listdir(os.path.join(srcs, path, file)))
            except:
                continue
            download = os.path.join('/directories', path, file)
            dirs.append({'path': file, 'num': num, 'download': download, 'read': read, 'write': write})
        else:
            # files.append(os.path.join(path, file))
            p = pathlib.Path(os.path.join(srcs, path, file))
            files.append({'path': file, 'size': sizeof_fmt(p.lstat().st_size), 'download': file, 'read': read, 'write': write})
    return files, dirs, True


# @login_required(redirect_field_name=None)
def files_view(request, path=''):
    if not request.user.is_authenticated:
        if request.GET.get('next') is not None:
            if 'logout' in request.GET.get('next'):
                return HttpResponseRedirect('/login')
        return HttpResponseRedirect(f'/login?next=/files/{path}')
    
    template = loader.get_template("files.html")
    if not os.path.isdir(os.path.join(srcs, path)):
        if path.endswith('/'):
            path = path[:-1]
        return download_single_file(path)
    
    context = get_context(request)
    context['navigator'] = get_navigator(path)
    files, dirs, canread = get_table(context, path, context['username'])
    # if len(files) + len(dirs) == 0:
    if not canread:
        raise Http404
    context['directories'] = dirs
    context['files'] = files
    context['path'] = path
    context['uploadfileform'] = UploadFileForm()

    return HttpResponse(template.render(context, request))


def logout_view(request):
    logout(request)
    return files_view(request)


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
        items = {}
        for key in request.POST:
            if key.startswith('write') and request.POST[key] == 'on':
                writes.append(key[6:])
                if key[6:] not in items:
                    items[key[6:]] = {'write': False, 'read': False}
                items[key[6:]]['write'] = True
            if key.startswith('read') and request.POST[key] == 'on':
                reads.append(key[5:])
                if key[5:] not in items:
                    items[key[5:]] = {'write': False, 'read': False}
                items[key[5:]]['read'] = True
        useraccesses = UserAccess.objects.filter(username=request.GET.get("user"), directory=path)
        for subpath, item in items.items():
            useraccess = useraccesses.filter(name=subpath)
            if len(useraccess) > 0:
                useraccess.update(
                    reads=item['read'],
                    writes=item['write'],
                )
            else:
                useraccess = UserAccess(
                    username=request.GET.get("user"),
                    directory=path,
                    name=subpath,
                    reads=item['read'],
                    writes=item['write'],
                )
                useraccess.save()
        return HttpResponse(b'success')

    else:
        template = loader.get_template("permissions.html")
        context = get_context(request)
        context['navigator'] = get_navigator(path, 'permission')
        files, dirs, canread = get_table(context, path, request.GET.get("user"))
        # print(path)
        # for di in dirs:
        #     print(di)
        context['directories'] = dirs
        context['files'] = files

        return HttpResponse(template.render(context, request))

def new_folder(request, path):
    if not request.user.is_authenticated:
        if request.GET.get('next') is not None:
            if 'logout' in request.GET.get('next'):
                return HttpResponseRedirect('/login')
        return HttpResponseRedirect(f'/login?next=/files/{path}')
    
    context = get_context(request)
    write = context['is_staff']
    useraccess = UserAccess.objects.filter(username=username, path=path)


def handle_uploaded_file(f, path):
    with open(os.path.join(srcs, path, f.name), "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def file_upload(request, path):
    if not request.user.is_authenticated:
        if request.GET.get('next') is not None:
            if 'logout' in request.GET.get('next'):
                return HttpResponseRedirect('/login')
        return HttpResponseRedirect(f'/login?next=/files/{path}')
    context = get_context(request)
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_uploaded_file(request.FILES["fileupload"], path)
    # return files_view(request, path)
    return HttpResponseRedirect(f'/files/{path}')


def folder_upload(request, path):
    if not request.user.is_authenticated:
        if request.GET.get('next') is not None:
            if 'logout' in request.GET.get('next'):
                return HttpResponseRedirect('/login')
        return HttpResponseRedirect(f'/login?next=/files/{path}')
    
    context = get_context(request)
