from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_profile_create, name="student_profile_create"),
]
