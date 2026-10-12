from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import StudentProfile


class InternalExeat(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending school review"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class ParentVerificationStatus(models.TextChoices):
        PENDING = "pending", "Awaiting parent-contact verification"
        CONFIRMED = "confirmed", "Parent confirmed"
        FAILED = "failed", "Parent could not be verified"

    # db_column preserves the legacy column created for the old field named `Profile`.
    # This lets the Python API use the consistent name `student` without dropping old data.
    student = models.ForeignKey(
        StudentProfile,
        db_column="Profile_id",
        on_delete=models.PROTECT,
        related_name="internal_exeats",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="internal_exeat_requests",
        null=True,
        blank=True,
        help_text="Account that submitted this request.",
    )
    purpose = models.CharField(max_length=200, help_text="e.g. Why are you going home?")
    destination = models.CharField(max_length=200, help_text="e.g. Pedu, Kotokraba")
    departure_date = models.DateField()
    departure_time = models.TimeField()
    return_date = models.DateField()
    return_time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    parent_verification_status = models.CharField(
        max_length=20,
        choices=ParentVerificationStatus.choices,
        default=ParentVerificationStatus.PENDING,
    )
    staff_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_internal_exeats",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "internal_exeat"
        ordering = ["-created_at"]
        verbose_name = "Internal exeat"
        verbose_name_plural = "Internal exeats"

    def clean(self):
        super().clean()
        if self.departure_date and self.return_date and self.return_date < self.departure_date:
            raise ValidationError({"return_date": "The return date cannot be before the departure date."})
        if (
            self.departure_date and self.departure_time and self.return_date and self.return_time
            and self.return_date == self.departure_date and self.return_time <= self.departure_time
        ):
            raise ValidationError({"return_time": "The return time must be after the departure time."})
        if self.departure_date and self.departure_time:
            departure_at = timezone.make_aware(
                datetime.combine(self.departure_date, self.departure_time),
                timezone.get_current_timezone(),
            ) if timezone.is_aware(timezone.now()) else datetime.combine(self.departure_date, self.departure_time)
            if departure_at < timezone.now():
                raise ValidationError({"departure_time": "Departure must be in the future."})
        if self.status == self.Status.APPROVED and self.parent_verification_status != self.ParentVerificationStatus.CONFIRMED:
            raise ValidationError({"status": "Confirm the parent through the school's official contact record before approving this exeat."})

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} — {self.purpose[:60]}"
