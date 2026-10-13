from unfold.admin import ModelAdmin
from django.contrib import admin

from .models import Classroom, StudentProfile
from .forms import StudentProfileForm


@admin.register(Classroom)
class ClassroomAdmin(ModelAdmin):
    list_display = ("code", "programme_name")
    search_fields = ("code", "programme_name")


@admin.register(StudentProfile)
class StudentProfileAdmin(ModelAdmin):
    form = StudentProfileForm

    list_display = (
        "first_name",
        "last_name",
        "year_admitted",
        "current_classroom",
        "house",
    )

    search_fields = (
        "first_name",
        "last_name",
        "email",
    )