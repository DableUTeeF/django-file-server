from django.contrib.auth.decorators import login_required
import os
from django.http import HttpResponse
from django.template import loader
from django.utils.encoding import smart_str
from django.contrib.auth import logout

srcs = '/nas' if os.path.exists('/nas') else '/home/palm/PycharmProjects/django-file-server/demofolder'


def get_context(request):
    context = {
        'username': request.user,
        'is_staff': request.user.is_staff,
    }

    return context

def download(path):
    response = HttpResponse(content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(os.path.basename(path))
    response['X-Sendfile'] = smart_str(path)
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
    for file in os.listdir(os.path.join(srcs, path)):
        print(path)
        print(file)
        if os.path.isdir(os.path.join(srcs, path, file)):
            # dirs.append(os.path.join(path, file) + '/')
            dirs.append(file + '/')
        else:
            # files.append(os.path.join(path, file))
            files.append(file)
    context['directories'] = sorted(dirs)
    context['files'] = sorted(files)

    return HttpResponse(template.render(context, request))

def logout_view(request):
    logout(request)
    return files(request)

