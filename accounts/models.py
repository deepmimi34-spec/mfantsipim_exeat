from django.db import models
from django.utils import timezone


class Classroom(models.Model):

    code = models.CharField(
        max_length=15,
        unique=True,
        help_text=(
            "Enter the class suffix only, e.g. S4, V3, G-Art or T. "
            "Do not include the form number."
        ),
    )

    programme_name = models.CharField(
        max_length=50,
        help_text="E.g. Visual Art, General Art or Technical",
    )

    class Meta:
        ordering = ["programme_name", "code"]

    def __str__(self):
        return f"{self.code} - {self.programme_name}"


class StudentProfile(models.Model):
    HOUSE_CHOICES = [
        ("Balmer Acquaah", "Balmer Acquaah"),
        ("Pickard Parker", "Pickard Parker"),
        ("Lockhart Schweitzer", "Lockhart Schweitzer"),
        ("Sarbah Picot", "Sarbah Picot"),
        ("Freeman Aggrey", "Freeman Aggrey"),
        ("Bartels Sneath", "Bartels Sneath"),
        ("Brandful Dontwi", "Brandful Dontwi"),
        ("Abruquah Monney", "Abruquah Monney"),
    ]

    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    year_admitted = models.PositiveSmallIntegerField(
        help_text="Year admitted, e.g. 2024"
    )

    admission_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Official student admission number",
    )

    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Store the permanent class group, not the changing form number.
    classroom_group = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="Classroom",
    )

    house = models.CharField(
        max_length=30,
        choices=HOUSE_CHOICES,
        default="Lockhart Schweitzer",
    )

    @property
    def current_form_number(self):
        current_year = timezone.localdate().year
        return current_year - self.year_admitted + 1

    @property
    def current_classroom(self):
        form_number = self.current_form_number

        if form_number < 1:
            return "Not yet admitted"

        if form_number > 3:
            return "Graduated"

        return f"{form_number}{self.classroom_group.code}"

    def __str__(self):
        return (
            f"{self.first_name} {self.last_name} "
            f"- {self.current_classroom}"
        )