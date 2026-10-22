
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from accounts.models import StudentProfile
from external_exeat.models import ExternalExeat
from internal_exeat.models import InternalExeat
from .models import GuardianInvitation, ParentProfile, StudentGuardian


class ExeatAdminSite(admin.AdminSite):
    site_header = "Mfantsipim Exeat Administration"
    site_title = "Mfantsipim Admin"
    index_title = "School Exeat Management"


def staff_dashboard_view(request):
    now = timezone.localtime()
    today = now.date()
    next_week = today + timedelta(days=7)

    internal = InternalExeat.objects.all()
    external = ExternalExeat.objects.all()

    pending_internal = internal.filter(status="pending").count()
    pending_external = external.filter(status="pending").count()

    verified_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.VERIFIED
    ).count()

    pending_links = StudentGuardian.objects.filter(
        status=StudentGuardian.Status.PENDING
    ).count()

    active_invitations = GuardianInvitation.objects.filter(
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=now,
    ).count()

    context = {
        **admin.site.each_context(request),
        "title": "Exeat Management Dashboard",
        "total_students": StudentProfile.objects.count(),
        "total_parents": ParentProfile.objects.count(),
        "total_guardian_links": StudentGuardian.objects.count(),
        "verified_links": verified_links,
        "pending_links": pending_links,
        "active_invitations": active_invitations,
        "total_internal": internal.count(),
        "total_external": external.count(),
        "pending_internal": pending_internal,
        "pending_external": pending_external,
        "approved_internal": internal.filter(status="approved").count(),
        "approved_external": external.filter(status="approved").count(),
        "rejected_internal": internal.filter(status="rejected").count(),
        "rejected_external": external.filter(status="rejected").count(),
        "upcoming_internal": internal.filter(
            status="approved",
            departure_date__range=(today, next_week),
        ).count(),
        "upcoming_external": external.filter(
            status="approved",
            departure_date__range=(today, next_week),
        ).count(),
        "internal_admin_url": reverse("admin:internal_exeat_internalexeat_changelist"),
        "external_admin_url": reverse("admin:external_exeat_externalexeat_changelist"),
        "students_admin_url": reverse("admin:accounts_studentprofile_changelist"),
        "parents_admin_url": reverse("admin:guardians_parentprofile_changelist"),
        "guardian_links_admin_url": reverse("admin:guardians_studentguardian_changelist"),
        "invitations_admin_url": reverse("admin:guardians_guardianinvitation_changelist"),
    }

    return TemplateResponse(
        request,
        "admin/guardians/exeat_dashboard.html",
        context,
    )
