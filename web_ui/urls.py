from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings
from django.views.generic.base import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url='files', permanent=True), name='index'),
    path("files/", views.files, name="file"),
    path("files/<str:path>/", views.files, name="file"),
]
