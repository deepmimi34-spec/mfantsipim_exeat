
from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import ExternalExeat


@admin.register(ExternalExeat)
class ExternalExeatAdmin(ModelAdmin):
    list_display = (
        "student",
        "requested_by",
        "departure_date",
        "departure_time",
        "return_date",
        "return_time",
        "parent_verification_status",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "parent_verification_status",
        "departure_date",
    )

    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_number",
        "requested_by__username",
        "requested_by__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "reviewed_by",
        "reviewed_at",
    )

    fields = (
        "student",
        "requested_by",
        "purpose",
        "destination",
        "departure_date",
        "departure_time",
        "return_date",
        "return_time",
        "parent_verification_status",
        "status",
        "staff_notes",
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Exeat requests should be submitted through the parent form.
        return False

    def save_model(self, request, obj, form, change):
        changed_review = not change

        if change:
            old_obj = ExternalExeat.objects.get(pk=obj.pk)

            changed_review = (
                old_obj.status != obj.status
                or old_obj.parent_verification_status
                != obj.parent_verification_status
            )

        if changed_review:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)