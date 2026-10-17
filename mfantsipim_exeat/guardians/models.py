import hashlib
from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import StudentProfile


class ParentProfile(models.Model):
    """Portal profile attached to the authenticated Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_profile",
    )
    phone = models.CharField(max_length=25, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.get_username()


class GuardianInvitation(models.Model):
    """A school-issued, single-use invitation sent to an official guardian email."""

    class Relationship(models.TextChoices):
        MOTHER = "mother", "Mother"
        FATHER = "father", "Father"
        LEGAL_GUARDIAN = "legal_guardian", "Legal guardian"
        OTHER = "other", "Other approved guardian"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="guardian_invitations",
    )
    guardian_name = models.CharField(max_length=150)
    guardian_email = models.EmailField(
        help_text="Use the guardian email address confirmed by the school.",
    )
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    token_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_guardian_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_guardian_invitations",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Guardian invitation"
        verbose_name_plural = "Guardian invitations"

    def clean(self):
        super().clean()
        if self.guardian_email:
            self.guardian_email = self.guardian_email.strip().lower()

    @property
    def invitation_state(self):
        if self.revoked_at:
            return "Revoked"
        if self.accepted_at:
            return "Accepted"
        if self.expires_at and self.expires_at <= timezone.now():
            return "Expired"
        return "Awaiting acceptance"

    def __str__(self):
        return f"{self.student} — invitation to {self.guardian_email}"


class StudentGuardian(models.Model):
    """Explicit authorization link between a parent account and one student."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        REVOKED = "revoked", "Revoked"