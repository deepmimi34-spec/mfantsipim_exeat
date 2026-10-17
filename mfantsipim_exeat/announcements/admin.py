from django.contrib import admin
from django.utils import timezone

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "author",
        "published_at",
        "updated_at",
    )
    list_filter = ("status", "published_at", "created_at")
    search_fields = ("title", "summary", "content", "author__username", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("author", "published_at", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    fieldsets = (
        ("Announcement", {"fields": ("title", "slug", "summary", "content")}),
        ("Publication", {"fields": ("status", "published_at")}),
        ("Audit information", {"fields": ("author", "created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        # Record which staff account created the announcement. Keep the original
        # author if another staff member later edits the post.
        if not change and obj.author_id is None:
            obj.author = request.user

        if obj.status == Announcement.Status.PUBLISHED and obj.published_at is None:
            obj.published_at = timezone.now()

        super().save_model(request, obj, form, change)
