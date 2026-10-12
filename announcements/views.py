from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Announcement


def announcement_list(request):
    """Show only published announcements, newest first, with pagination."""
    published = Announcement.objects.filter(
        status=Announcement.Status.PUBLISHED
    ).select_related("author")
    paginator = Paginator(published, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "announcements/announcement_list.html",
        {"page_obj": page_obj, "page_title": "Announcements | Mfantsipim School"},
    )


def announcement_detail(request, slug):
    """Publicly display a published announcement only."""
    announcement = get_object_or_404(
        Announcement.objects.select_related("author"),
        slug=slug,
        status=Announcement.Status.PUBLISHED,
    )
    return render(
        request,
        "announcements/announcement_detail.html",
        {
            "announcement": announcement,
            "page_title": f"{announcement.title} | Mfantsipim School",
        },
    )
