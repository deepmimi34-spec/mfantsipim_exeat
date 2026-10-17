from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from guardians.decorators import parent_required
from guardians.models import ParentProfile, StudentGuardian
from .forms import ExternalExeatForm
from .models import ExternalExeat


@parent_required
def external_exeat_create(request):
    """Submit an external exeat for a child verified against the signed-in parent."""
    parent_profile, _ = ParentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ExternalExeatForm(request.POST, parent_profile=parent_profile)
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
                    exeat.status = ExternalExeat.Status.PENDING
                    exeat.parent_verification_status = ExternalExeat.ParentVerificationStatus.PENDING
                    exeat.save()
                    messages.success(
                        request,
                        "Your external exeat request has been submitted. It is awaiting the school's parent-contact verification and approval.",
                    )
                    return redirect("external_exeat:external_exeat_create")
    else:
        form = ExternalExeatForm(parent_profile=parent_profile)

    has_verified_children = StudentGuardian.objects.filter(
        parent=parent_profile,
        status=StudentGuardian.Status.VERIFIED,
    ).exists()
    return render(
        request,
        "exeat/external.html",
        {
            "form": form,
            "page_title": "Apply for an external exeat",
            "has_verified_children": has_verified_children,
        },
    )
