from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import StudentProfileForm


def student_profile_create(request):
    """Display and process the student profile creation form."""
    if request.method == "POST":
        form = StudentProfileForm(request.POST)

        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                (
                    f"Student profile for {student.first_name} "
                    f"{student.last_name} was saved successfully. "
                    f"Current classroom: {student.current_classroom}."
                ),
            )
            return redirect("external_exeat:external_exeat_create")
    else:
        form = StudentProfileForm()

    return render(
        request,
        "students/student_profile_form.html",
        {"form": form, "page_title": "Create Student Profile"},
    )

# Create your views here.
