from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Announcement


class AnnouncementPublicPageTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="schooladmin", password="test-password-123"
        )

    def test_published_announcement_appears_on_list(self):
        Announcement.objects.create(
            title="School News",
            content="The school has an important update.",
            author=self.author,
            status=Announcement.Status.PUBLISHED,
        )
        response = self.client.get(reverse("announcements:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School News")

    def test_draft_announcement_is_not_public(self):
        Announcement.objects.create(
            title="Unpublished News",
            content="This is not ready for publication.",
            author=self.author,
            status=Announcement.Status.DRAFT,
        )
        response = self.client.get(reverse("announcements:list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Unpublished News")

    def test_draft_detail_returns_404(self):
        draft = Announcement.objects.create(
            title="Private Draft",
            content="Draft only.",
            author=self.author,
            status=Announcement.Status.DRAFT,
        )
        response = self.client.get(
            reverse("announcements:detail", kwargs={"slug": draft.slug})
        )
        self.assertEqual(response.status_code, 404)
