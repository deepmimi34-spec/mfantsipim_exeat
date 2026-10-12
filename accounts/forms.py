from django import forms
from django.utils import timezone

from .models import StudentProfile, Classroom


class ClassroomChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # JavaScript will add the current form number.
        return f"{obj.code} — {obj.programme_name}"


class StudentProfileForm(forms.ModelForm):
    year_admitted = forms.TypedChoiceField(
        coerce=int,
        choices=[],
        label="Year Admitted",
    )

    classroom_group = ClassroomChoiceField(
        queryset=Classroom.objects.none(),
        label="Classroom",
        empty_label="Select a classroom",
    )

    class Meta:
        model = StudentProfile
        fields = [
            "first_name",
            "last_name",
            "year_admitted",
            "email",
            "phone",
            "classroom_group",
            "house",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = timezone.localdate().year
        existing_year = getattr(
            self.instance, "year_admitted", None
        )

        # Generate admission years automatically.
        years = set(range(2024, current_year + 1))

        if existing_year:
            years.add(existing_year)

        self.fields["year_admitted"].choices = [
            (year, str(year))
            for year in sorted(years, reverse=True)
        ]

        # Get all available classroom groups from the database.
        self.fields["classroom_group"].queryset = (
            Classroom.objects.all()
        )

    class Media:
        js = ("students/js/student_profile_form.js",)