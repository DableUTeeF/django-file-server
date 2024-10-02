from django.contrib.auth.decorators import login_required
import os
from django.http import HttpResponse
from django.template import loader
from django.utils.encoding import smart_str
from django.contrib.auth import logout
from django.http import StreamingHttpResponse
import mimetypes
from wsgiref.util import FileWrapper


srcs = '/nas' if os.path.exists('/nas') else '/home/palm/PycharmProjects/django-file-server/demofolder'


def get_context(request):
    context = {
        'username': request.user,
        'is_staff': request.user.is_staff,
    }

    return context


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


@login_required(redirect_field_name=None)
def files(request, path=''):
    template = loader.get_template("files.html")
    if not os.path.isdir(os.path.join(srcs, path)):
        return download(path)
    context = {
        'current_path': path + '/'
    }
    files = []
    dirs = []
    for file in sorted(os.listdir(os.path.join(srcs, path))):
        print(path)
        print(file)
        if os.path.isdir(os.path.join(srcs, path, file)):
            # dirs.append(os.path.join(path, file) + '/')
            try:
                num = len(os.listdir(os.path.join(srcs, path, file)))
            except:
                continue
            dirs.append({'path': file + '/', 'num': num})
        else:
            # files.append(os.path.join(path, file))
            files.append(file)
    context['directories'] = dirs
    context['files'] = files

    return HttpResponse(template.render(context, request))

def logout_view(request):
    logout(request)
    return files(request)

