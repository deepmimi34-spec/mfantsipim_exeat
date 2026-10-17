from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from guardians.decorators import parent_required
from guardians.models import ParentProfile, StudentGuardian
from .forms import InternalExeatForm
from .models import InternalExeat


@parent_required
def internal_exeat(request):
    """Submit an internal exeat for a child verified against the signed-in parent."""
    parent_profile, _ = ParentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = InternalExeatForm(request.POST, parent_profile=parent_profile)
        if form.is_valid():
            with transaction.atomic():
                link = StudentGuardian.objects.select_for_update().filter(
                    parent=parent_profile,
                    student=form.cleaned_data["student"],
                    status=StudentGuardian.Status.VERIFIED,
                ).first()
                if link is None:
                    form.add_error("student", "You are not authorised to request an exeat for this student.")
                else:
                    exeat = form.save(commit=False)
                    exeat.student = link.student
                    exeat.requested_by = request.user
                    exeat.status = InternalExeat.Status.PENDING
                    exeat.parent_verification_status = InternalExeat.ParentVerificationStatus.PENDING
                    exeat.save()
                    messages.success(
                        request,
                        "Your internal exeat request has been submitted. It is awaiting the school's parent-contact verification and approval.",
                    )
                    return redirect("internal_exeat:internal_exeat_create")
    else:
        form = InternalExeatForm(parent_profile=parent_profile)

    has_verified_children = StudentGuardian.objects.filter(
        parent=parent_profile,
        status=StudentGuardian.Status.VERIFIED,
    ).exists()
    return render(
        request,
        "exeat/internal.html",
        {
            "form": form,
            "page_title": "Apply for an internal exeat",
            "has_verified_children": has_verified_children,
        },
    )
