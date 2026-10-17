from datetime import datetime

from django import forms
from django.utils import timezone

from accounts.models import StudentProfile
from .models import ParentProfile, StudentGuardian


class ParentChildExeatFormMixin:
    """Limit the student selector to children linked to this verified parent."""

    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(),
        label="Student",
        empty_label="Select your child",
        widget=forms.Select(attrs={"class": "form-control", "id": "student"}),
    )

    def __init__(self, *args, parent_profile: ParentProfile | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if parent_profile is not None:
            child_ids = StudentGuardian.objects.filter(
                parent=parent_profile,
                status=StudentGuardian.Status.VERIFIED,
            ).values_list("student_id", flat=True)
            self.fields["student"].queryset = StudentProfile.objects.filter(pk__in=child_ids).distinct()
        for field_name, field in self.fields.items():
            if field_name != "student":
                current_class = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{current_class} form-control".strip()

    def clean(self):
        cleaned_data = super().clean()
        departure_date = cleaned_data.get("departure_date")
        departure_time = cleaned_data.get("departure_time")
        return_date = cleaned_data.get("return_date")
        return_time = cleaned_data.get("return_time")

        if departure_date and departure_date < timezone.localdate():
            self.add_error("departure_date", "Departure date cannot be in the past.")

        if all([departure_date, departure_time, return_date, return_time]):
            departure_at = datetime.combine(departure_date, departure_time)
            return_at = datetime.combine(return_date, return_time)
            now = timezone.now()
            if timezone.is_aware(now):
                current_timezone = timezone.get_current_timezone()
                departure_at = timezone.make_aware(departure_at, current_timezone)
                return_at = timezone.make_aware(return_at, current_timezone)
                now = timezone.localtime(now, current_timezone)
            if departure_at < now:
                self.add_error("departure_time", "Departure must be in the future.")
            if return_at <= departure_at:
                self.add_error("return_date", "The return date and time must be after the departure date and time.")
        return cleaned_data
