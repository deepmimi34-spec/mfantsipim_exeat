from django.urls import path

from . import views

app_name = "internal_exeat"

urlpatterns = [
    path('internal_exeat/', views.internal_exeat, name='internal_exeat'),
]
