from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from reddit_data.models import AnalysisResult, RedditPost


def make_post(post_id, subreddit, created_utc):
    return RedditPost.objects.create(
        post_id=post_id,
        title=f"Post {post_id}",
        subreddit=subreddit,
        permalink=f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/",
        search_term="term",
        created_utc=created_utc,
    )


class AnalyticsDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pw"
        )
        self.client.force_login(self.user)

        jan = timezone.datetime(2026, 1, 15, tzinfo=timezone.get_current_timezone())
        feb = timezone.datetime(2026, 2, 10, tzinfo=timezone.get_current_timezone())

        post1 = make_post("p1", "sales", jan)
        post2 = make_post("p2", "sales", feb)
        post3 = make_post("p3", "marketing", jan)

        AnalysisResult.objects.create(
            post=post1, pain_point="Manual lead gen", sentiment="negative", is_high_intent=True
        )
        AnalysisResult.objects.create(
            post=post2, pain_point="Manual lead gen", sentiment="negative", is_high_intent=True
        )
        AnalysisResult.objects.create(
            post=post3, pain_point="Too many tools", sentiment="neutral", is_high_intent=False
        )

    def test_dashboard_requires_staff_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin:reddit_data_analytics"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_aggregated_data(self):
        response = self.client.get(reverse("admin:reddit_data_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual lead gen")
        self.assertContains(response, "r/sales")
        self.assertContains(response, "r/marketing")

    def test_dashboard_linked_from_admin_index(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, reverse("admin:reddit_data_analytics"))
