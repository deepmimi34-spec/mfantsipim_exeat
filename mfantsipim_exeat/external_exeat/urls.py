from django.urls import path

from . import views

app_name = "external_exeat"

urlpatterns = [
    path("external_exeat/", views.external_exeat_create, name="external_exeat_create"),
]
