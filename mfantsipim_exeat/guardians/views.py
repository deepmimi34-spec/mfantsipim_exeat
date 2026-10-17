import hashlib

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from external_exeat.models import ExternalExeat
from internal_exeat.models import InternalExeat
from .decorators import has_verified_google_identity, parent_required
from .models import GuardianInvitation, ParentProfile, StudentGuardian


def parent_login_info(request):
    """Small landing page that directs parents to Google sign-in."""
    return render(request, "guardians/login_info.html")


@parent_required
def parent_dashboard(request):
    parent, _ = ParentProfile.objects.get_or_create(user=request.user)
    children = (
        StudentGuardian.objects.filter(
            parent=parent,
            status=StudentGuardian.Status.VERIFIED,
        )
        .select_related("student", "student__classroom_group")
    )
    internal_requests = (
        InternalExeat.objects.filter(
            student__guardian_links__parent=parent,
            student__guardian_links__status=StudentGuardian.Status.VERIFIED,
            requested_by=request.user,
        )
        .select_related("student")
        .distinct()
        .order_by("-created_at")[:10]
    )
    external_requests = (
        ExternalExeat.objects.filter(
            student__guardian_links__parent=parent,
            student__guardian_links__status=StudentGuardian.Status.VERIFIED,
            requested_by=request.user,
        )
        .select_related("student")
        .distinct()
        .order_by("-created_at")[:10]
    )
    return render(
        request,
        "guardians/dashboard.html",
        {
            "parent_profile": parent,
            "children": children,
            "internal_requests": internal_requests,
            "external_requests": external_requests,
        },
    )


@login_required(login_url="/accounts/login/")
def accept_invitation(request, token):
    """Accept a school invitation only from its exact verified Google email."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = get_object_or_404(GuardianInvitation, token_hash=token_hash)

    if invitation.revoked_at:
        messages.error(request, "This invitation has been revoked. Please contact the school.")
        return redirect("account_login")
    if invitation.accepted_at:
        messages.info(request, "This invitation has already been used. Sign in to view your parent portal.")
        return redirect("guardians:dashboard")
    if not invitation.expires_at or invitation.expires_at <= timezone.now():
        messages.error(request, "This invitation has expired. Please contact the school for a new invitation.")
        return redirect("account_login")

    if not has_verified_google_identity(request.user):
        logout(request)
        messages.error(request, "Use Google sign-in with a verified email address to accept this invitation. Open the invitation link again after signing in.")
        return redirect("account_login")

    if request.user.email.strip().casefold() != invitation.guardian_email.strip().casefold():
        # Do not expose student details to an account other than the invited account.
        logout(request)
        messages.error(request, "This invitation was sent to a different email address. Sign in with the invited Google account, then open the invitation link again.")
        return redirect("account_login")

    if request.method == "POST":
        with transaction.atomic():
            invitation = GuardianInvitation.objects.select_for_update().get(pk=invitation.pk)
            if invitation.accepted_at or invitation.revoked_at or not invitation.expires_at or invitation.expires_at <= timezone.now():
                messages.error(request, "This invitation is no longer valid. Please contact the school.")
                return redirect("guardians:dashboard")

            parent, _ = ParentProfile.objects.get_or_create(user=request.user)
            link, created = StudentGuardian.objects.get_or_create(
                student=invitation.student,
                parent=parent,
                defaults={
                    "relationship": invitation.relationship,
                    "status": StudentGuardian.Status.VERIFIED,
                    "verification_method": StudentGuardian.VerificationMethod.INVITATION,
                    "invitation": invitation,
                    "verified_at": timezone.now(),
                },
            )
            if not created:
                link.relationship = invitation.relationship
                link.status = StudentGuardian.Status.VERIFIED
                link.verification_method = StudentGuardian.VerificationMethod.INVITATION
                link.invitation = invitation
                link.verified_at = timezone.now()
                link.verified_by = None
                link.save(update_fields=[
                    "relationship", "status", "verification_method", "invitation",
                    "verified_at", "verified_by", "updated_at",
                ])

            invitation.accepted_at = timezone.now()
            invitation.accepted_by = request.user
            invitation.save(update_fields=["accepted_at", "accepted_by"])

        messages.success(request, "Your child has been linked to your parent portal successfully.")
        return redirect("guardians:dashboard")

    return render(request, "guardians/accept_invitation.html", {"invitation": invitation})
