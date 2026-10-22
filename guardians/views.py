import hashlib

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import has_verified_google_identity, parent_required



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


@parent_required
def link_child(request):
    """
    Let a signed-in parent request a link to a student.
    The school must verify the relationship before access is granted.
    """
    parent_profile, _ = ParentProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        student_number = (
            request.POST.get("student_number", "").strip()
        )
        supplied_name = " ".join(
            request.POST.get("student_full_name", "").split()
        ).casefold()
        relationship = (
            request.POST.get("relationship", "").strip()
        )

        allowed_relationships = {
            "father",
            "mother",
            "guardian",
            "other",
        }

        if not student_number or not supplied_name or not relationship:
            messages.error(
                request,
                "Please complete all the required fields."
            )

        elif relationship.casefold() not in allowed_relationships:
            messages.error(
                request,
                "Please select a valid relationship."
            )

        else:
            try:
                student = StudentProfile.objects.get(
                    admission_number__iexact=student_number
                )
            except StudentProfile.DoesNotExist:
                student = None

            if student is None:
                messages.error(
                    request,
                    "We could not verify those student details. "
                    "Check the admission number and full name."
                )
            else:
                official_name = " ".join(
                    part for part in [
                        student.first_name,
                        student.last_name,
                    ] if part
                ).casefold()

                if supplied_name != official_name:
                    messages.error(
                        request,
                        "We could not verify those student details. "
                        "Check the admission number and full name."
                    )
                else:
                    with transaction.atomic():
                        existing_request = (
                            StudentGuardian.objects.filter(
                                parent=parent_profile,
                                student=student,
                            ).first()
                        )

                        if existing_request:
                            messages.info(
                                request,
                                "A link request for this student "
                                "already exists. Please contact "
                                "the school if you need assistance."
                            )
                        else:
                            StudentGuardian.objects.create(
                                parent=parent_profile,
                                student=student,
                                relationship=relationship,
                                status=StudentGuardian.Status.PENDING,
                            )

                            messages.success(
                                request,
                                "Your request has been submitted. "
                                "The school must verify your "
                                "relationship before access is granted."
                            )

                            return redirect("guardians:link_child")

    existing_links = StudentGuardian.objects.filter(
        parent=parent_profile
    ).select_related("student")

    return render(
        request,
        "guardians/link_child.html",
        {
            "existing_links": existing_links,
            "page_title": "Link Your Child",
        },
    )


from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.models import StudentProfile
from external_exeat.models import ExternalExeat
from internal_exeat.models import InternalExeat
from guardians.models import (
    GuardianInvitation,
    ParentProfile,
    StudentGuardian,
)


@staff_member_required
def staff_dashboard(request):
    """Central overview for authorised school staff."""

    today = timezone.localdate()
    now = timezone.localtime()
    current_time = now.time()
    next_week = today + timedelta(days=7)
    since = now - timedelta(days=180)

    User = get_user_model()

    # Core records
    total_students = StudentProfile.objects.count()
    total_parents = ParentProfile.objects.count()
    active_accounts = User.objects.filter(is_active=True).count()

    total_links = StudentGuardian.objects.count()
    verified_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.VERIFIED
    ).count()
    pending_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.PENDING
    ).count()
    rejected_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.REJECTED
    ).count()

    # Invitations that have not been accepted, revoked or expired
    active_invitations = GuardianInvitation.objects.filter(
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).count()

    internal = InternalExeat.objects.all()
    external = ExternalExeat.objects.all()

    internal_pending = internal.filter(
        status__in=[
            InternalExeat.Status.PENDING,
            InternalExeat.Status.UNDER_REVIEW,
        ]
    )
    external_pending = external.filter(
        status__in=[
            ExternalExeat.Status.PENDING,
            ExternalExeat.Status.UNDER_REVIEW,
        ]
    )

    total_internal = internal.count()
    total_external = external.count()
    total_exeats = total_internal + total_external

    pending_internal_count = internal_pending.count()
    pending_external_count = external_pending.count()
    pending_exeats = pending_internal_count + pending_external_count

    approved_exeats = (
        internal.filter(status=InternalExeat.Status.APPROVED).count()
        + external.filter(status=ExternalExeat.Status.APPROVED).count()
    )

    rejected_exeats = (
        internal.filter(status=InternalExeat.Status.REJECTED).count()
        + external.filter(status=ExternalExeat.Status.REJECTED).count()
    )

    awaiting_parent_confirmation = (
        internal.filter(
            parent_verification_status=(
                InternalExeat.ParentVerificationStatus.PENDING
            )
        ).exclude(
            status__in=[
                InternalExeat.Status.CANCELLED,
                InternalExeat.Status.REJECTED,
            ]
        ).count()
        + external.filter(
            parent_verification_status=(
                ExternalExeat.ParentVerificationStatus.PENDING
            )
        ).exclude(
            status__in=[
                ExternalExeat.Status.CANCELLED,
                ExternalExeat.Status.REJECTED,
            ]
        ).count()
    )

    # Approved departures over the next seven days, including today
    departure_window = (
        Q(departure_date__gt=today, departure_date__lte=next_week)
        | Q(departure_date=today, departure_time__gte=current_time)
    )

    upcoming_internal = internal.filter(
        departure_window,
        status=InternalExeat.Status.APPROVED,
    ).select_related("student").order_by(
        "departure_date", "departure_time"
    )

    upcoming_external = external.filter(
        departure_window,
        status=ExternalExeat.Status.APPROVED,
    ).select_related("student").order_by(
        "departure_date", "departure_time"
    )

    # Approved exeats whose return time has passed
    overdue_returns = (
        internal.filter(status=InternalExeat.Status.APPROVED)
        .filter(
            Q(return_date__lt=today)
            | Q(return_date=today, return_time__lt=current_time)
        ).select_related("student")
    )

    overdue_external = (
        external.filter(status=ExternalExeat.Status.APPROVED)
        .filter(
            Q(return_date__lt=today)
            | Q(return_date=today, return_time__lt=current_time)
        ).select_related("student")
    )

    # Parent–child link requests needing school review
    recent_pending_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.PENDING
    ).select_related(
        "parent__user", "student"
    ).order_by("-created_at")[:8]

    # Requests needing attention
    recent_internal_pending = internal_pending.select_related(
        "student", "requested_by"
    ).order_by("-created_at")[:8]

    recent_external_pending = external_pending.select_related(
        "student", "requested_by"
    ).order_by("-created_at")[:8]

    # Monthly exeat volume for the last six months
    internal_monthly = {
        row["month"].date() if hasattr(row["month"], "date")
        else row["month"]: row["total"]
        for row in internal.filter(created_at__gte=since)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
    }

    external_monthly = {
        row["month"].date() if hasattr(row["month"], "date")
        else row["month"]: row["total"]
        for row in external.filter(created_at__gte=since)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
    }

    month_starts = []
    year, month = today.year, today.month

    for _ in range(6):
        month_starts.append(today.replace(day=1, year=year, month=month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    month_starts.reverse()

    chart_labels = [
        month_start.strftime("%b %Y") for month_start in month_starts
    ]
    chart_internal = [
        internal_monthly.get(month_start, 0)
        for month_start in month_starts
    ]
    chart_external = [
        external_monthly.get(month_start, 0)
        for month_start in month_starts
    ]

    context = {
        "total_students": total_students,
        "total_parents": total_parents,
        "active_accounts": active_accounts,
        "total_links": total_links,
        "verified_links": verified_links,
        "pending_links": pending_links,
        "rejected_links": rejected_links,
        "active_invitations": active_invitations,
        "total_internal": total_internal,
        "total_external": total_external,
        "total_exeats": total_exeats,
        "pending_internal_count": pending_internal_count,
        "pending_external_count": pending_external_count,
        "pending_exeats": pending_exeats,
        "approved_exeats": approved_exeats,
        "rejected_exeats": rejected_exeats,
        "awaiting_parent_confirmation": awaiting_parent_confirmation,
        "upcoming_internal": upcoming_internal[:8],
        "upcoming_external": upcoming_external[:8],
        "overdue_returns": overdue_returns[:8],
        "overdue_external": overdue_external[:8],
        "recent_pending_links": recent_pending_links,
        "recent_internal_pending": recent_internal_pending,
        "recent_external_pending": recent_external_pending,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_internal_json": json.dumps(chart_internal),
        "chart_external_json": json.dumps(chart_external),
    }

    return render(request, "guardians/staff_dashboard.html", context)
