from django.contrib.auth.decorators import login_required
import os
from django.http import HttpResponse
from django.template import loader
from django.utils.encoding import smart_str
from django.contrib.auth import logout
from django.http import StreamingHttpResponse
import mimetypes
from wsgiref.util import FileWrapper
import pathlib

srcs = '/nas' if os.path.exists('/nas') else '/home/palm/PycharmProjects/django-file-server/demofolder'


def get_context(request):
    context = {
        'username': request.user,
        'is_staff': request.user.is_staff,
    }

    return context


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{int(num)}{unit}{suffix}"
        num /= 1024.0
    return f"{int(num)}Yi{suffix}"


def download(path):
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

def get_navigator(path):
    # <a href="{{ current_path }}">{{ current_path }}</a>
    nav = '<a href="/files/">HOME</a>/'
    chunks = path.split('/')
    for i, chunk in enumerate(chunks):
        if chunk == '':
            continue
        href = os.path.join(*chunks[:i+1])
        nav += f'<a href="/files/{href}">{chunk}</a>/'
    return nav

@login_required(redirect_field_name=None)
def files(request, path=''):
    template = loader.get_template("files.html")
    if not os.path.isdir(os.path.join(srcs, path)):
        if path.endswith('/'):
            path = path[:-1]
        return download(os.path.join(srcs, path))
    
    context = {
        # 'current_path': '/' + path
        'navigator': get_navigator(path)
    }
    files = []
    dirs = []
    for file in sorted(os.listdir(os.path.join(srcs, path))):
        if os.path.isdir(os.path.join(srcs, path, file)):
            # dirs.append(os.path.join(path, file) + '/')
            try:
                num = len(os.listdir(os.path.join(srcs, path, file)))
            except:
                continue
            dirs.append({'path': file, 'num': num})
        else:
            # files.append(os.path.join(path, file))
            p = pathlib.Path(os.path.join(srcs, path, file))
            files.append({'path': file, 'size': sizeof_fmt(p.lstat().st_size)})
    context['directories'] = dirs
    context['files'] = files

    return HttpResponse(template.render(context, request))

def logout_view(request):
    logout(request)
    return files(request)

