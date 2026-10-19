from django.urls import path

from . import views

app_name = "internal_exeat"

urlpatterns = [
    path('', views.internal_exeat, name='internal_exeat'),
]
