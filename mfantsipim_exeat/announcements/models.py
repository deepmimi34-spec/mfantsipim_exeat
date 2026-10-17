from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Announcement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(
        max_length=300,
        blank=True,
        help_text="A short preview shown on the announcements page (optional).",
    )
    content = models.TextField(help_text="Write the announcement in plain text.")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="school_announcements",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PUBLISHED,
        help_text="Only published announcements appear on the public website.",
    )
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        verbose_name = "announcement"
        verbose_name_plural = "announcements"

    def save(self, *args, **kwargs):
        # Generate a URL-friendly slug and keep it unique.
        slug_source = self.slug.strip() or self.title
        base_slug = slugify(slug_source) or "announcement"
        candidate = base_slug[:220]
        suffix = 2

        while (
            type(self).objects.filter(slug=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            suffix_text = f"-{suffix}"
            candidate = f"{base_slug[:220 - len(suffix_text)]}{suffix_text}"
            suffix += 1

        self.slug = candidate

        # Set the publication timestamp the first time an item is published.
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
