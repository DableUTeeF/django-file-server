from django.urls import path, re_path
from django.conf.urls.static import static
from . import views
from django.conf import settings
from django.views.generic.base import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url='files', permanent=True), name='index'),
    path("files/", views.files, name="file"),
    path("gethash/", views.gethash, name="gethash"),
    re_path(r"^download/(?P<hash>([^/]+/)*)$", views.hash_download, name="hash_download"),
    re_path(r"^directories/(?P<path>([^/]+/)*)$", views.download, name="download"),
    re_path(r"^files/(?P<path>([^/]+/)*)$", views.files, name="file"),  # (?P<path>([^/]+/)*)$
    re_path(r"^permission/(?P<path>([^/]+/)*)$", views.permission_view, name="file"),  # (?P<path>([^/]+/)*)$
]
