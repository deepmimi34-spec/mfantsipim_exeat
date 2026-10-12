from django.urls import path
from . import views

app_name = "guardians"

urlpatterns = [
    path("login/", views.parent_login_info, name="login_info"),
    path("dashboard/", views.parent_dashboard, name="dashboard"),
    path("invitations/<str:token>/accept/", views.accept_invitation, name="accept_invitation"),
]
