import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import GuardianInvitation, ParentProfile, StudentGuardian


@admin.register(ParentProfile)
class ParentProfileAdmin(ModelAdmin):
    list_display = ("user", "email", "phone", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    readonly_fields = ("user", "created_at", "updated_at")

    def has_add_permission(self, request):
        # Parent profiles are created on invitation acceptance or first portal visit.
        return False

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email


@admin.register(StudentGuardian)
class StudentGuardianAdmin(ModelAdmin):

    def save_model(self, request, obj, form, change):
        if obj.status == StudentGuardian.Status.VERIFIED and not obj.verified_at:
            obj.verified_at = timezone.now()
            obj.verified_by = request.user
            obj.verification_method = StudentGuardian.VerificationMethod.STAFF
        elif obj.status != StudentGuardian.Status.VERIFIED:
            obj.verified_at = None
            obj.verified_by = None
        super().save_model(request, obj, form, change)


@admin.register(GuardianInvitation)
class GuardianInvitationAdmin(ModelAdmin):
    list_display = (
        "student", "guardian_name", "guardian_email", "relationship",
        "invitation_state", "expires_at", "created_by", "created_at",
    )
    list_filter = ("relationship", "created_at")
    search_fields = (
        "student__first_name", "student__last_name", "student__admission_number",
        "guardian_name", "guardian_email",
    )
    readonly_fields = (
        "created_by", "created_at", "expires_at", "accepted_at",
        "accepted_by", "revoked_at",
    )
    exclude = ("token_hash",)
    actions = ("reissue_invitations", "revoke_invitations")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            # Do not silently change the recipient/student after a token was issued.
            fields.extend(["student", "guardian_name", "guardian_email", "relationship"])
        return tuple(fields)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        if is_new:
            raw_token = secrets.token_urlsafe(32)
            obj.token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            obj.expires_at = timezone.now() + timedelta(days=3)
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
            self._send_invitation(request, obj, raw_token)
            return
        super().save_model(request, obj, form, change)

    def _send_invitation(self, request, invitation, raw_token):
        link = request.build_absolute_uri(
            reverse("guardians:accept_invitation", kwargs={"token": raw_token})
        )
        subject = "Mfantsipim School parent portal invitation"
        body = (
            f"Dear {invitation.guardian_name},\n\n"
            "The school has invited you to securely link your parent account to a student record.\n"
            "Sign in with the Google account at this invited email address, then open this link:\n\n"
            f"{link}\n\n"
            "This invitation expires in 3 days and can only be used once. If you were not expecting it, contact the school.\n"
        )
        try:
            sent = send_mail(
                subject,
                body,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [invitation.guardian_email],
                fail_silently=False,
            )
            if sent:
                self.message_user(request, f"Invitation sent to {invitation.guardian_email}.", messages.SUCCESS)
            else:
                self.message_user(request, "The invitation was saved, but the email backend did not report a sent message. Use 'Reissue invitations' after checking email settings.", messages.WARNING)
        except Exception as exc:  # email backend errors should not erase the saved invitation
            self.message_user(
                request,
                f"Invitation was saved, but email sending failed ({exc.__class__.__name__}). Check EMAIL settings, then use 'Reissue invitations'.",
                messages.WARNING,
            )

    @admin.action(description="Reissue selected guardian invitations")
    def reissue_invitations(self, request, queryset):
        sent_count = 0
        skipped_count = 0
        for invitation in queryset:
            if invitation.accepted_at or invitation.revoked_at:
                skipped_count += 1
                continue
            raw_token = secrets.token_urlsafe(32)
            invitation.token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            invitation.expires_at = timezone.now() + timedelta(days=3)
            invitation.save(update_fields=["token_hash", "expires_at"])
            link = request.build_absolute_uri(
                reverse("guardians:accept_invitation", kwargs={"token": raw_token})
            )
            body = (
                f"Dear {invitation.guardian_name},\n\n"
                "Here is your renewed Mfantsipim School parent portal invitation.\n"
                f"Sign in with Google using {invitation.guardian_email}, then open:\n\n{link}\n\n"
                "This link expires in 3 days and can be used once.\n"
            )
            try:
                sent = send_mail(
                    "Mfantsipim School parent portal invitation",
                    body,
                    getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    [invitation.guardian_email],
                    fail_silently=False,
                )
                sent_count += bool(sent)
            except Exception:
                skipped_count += 1
        self.message_user(
            request,
            f"Reissued {sent_count} invitation(s). {skipped_count} were skipped or had email errors.",
            messages.WARNING if skipped_count else messages.SUCCESS,
        )

    @admin.action(description="Revoke selected unused guardian invitations")
    def revoke_invitations(self, request, queryset):
        count = queryset.filter(accepted_at__isnull=True, revoked_at__isnull=True).update(revoked_at=timezone.now())
        self.message_user(request, f"Revoked {count} unused invitation(s).", messages.SUCCESS)
