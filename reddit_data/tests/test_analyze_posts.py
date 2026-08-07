from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from reddit_data.models import AnalysisResult, Comment, DraftReply, RedditPost


def fake_tool_use_response(pain_point, sentiment, is_high_intent, proposed_reply):
    tool_use_block = SimpleNamespace(
        type="tool_use",
        input={
            "pain_point": pain_point,
            "sentiment": sentiment,
            "is_high_intent": is_high_intent,
            "proposed_reply": proposed_reply,
        },
    )
    return SimpleNamespace(content=[tool_use_block])


class AnalyzePostsCommandTests(TestCase):
    def setUp(self):
        self.post = RedditPost.objects.create(
            post_id="p1",
            title="Struggling with lead gen",
            text="Our current process is too manual.",
            subreddit="sales",
            permalink="https://www.reddit.com/r/sales/comments/p1/",
            search_term="lead gen",
            created_utc=timezone.now(),
        )
        Comment.objects.create(
            post=self.post,
            comment_id="c1",
            text="Try automating it",
            score=4,
            permalink="https://www.reddit.com/r/sales/comments/p1/c1/",
        )

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CommandError):
                call_command("analyze_posts", stdout=StringIO())

    @patch("reddit_data.management.commands.analyze_posts.anthropic.Anthropic")
    def test_analyzes_unanalyzed_post(self, mock_anthropic_cls):
        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = fake_tool_use_response(
            pain_point="Manual lead gen process",
            sentiment="negative",
            is_high_intent=True,
            proposed_reply="Sounds frustrating - have you looked at automating the first step?",
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
            call_command("analyze_posts", stdout=StringIO())

        self.assertEqual(AnalysisResult.objects.count(), 1)
        analysis = AnalysisResult.objects.get(post=self.post)
        self.assertEqual(analysis.sentiment, "negative")
        self.assertTrue(analysis.is_high_intent)

        self.assertEqual(DraftReply.objects.count(), 1)
        draft = DraftReply.objects.get(post=self.post)
        self.assertEqual(draft.status, "pending")
        self.assertIn("automating", draft.proposed_text)

    @patch("reddit_data.management.commands.analyze_posts.anthropic.Anthropic")
    def test_skips_already_analyzed_posts(self, mock_anthropic_cls):
        AnalysisResult.objects.create(post=self.post, sentiment="neutral")
        mock_client = mock_anthropic_cls.return_value

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
            call_command("analyze_posts", stdout=StringIO())

        mock_client.messages.create.assert_not_called()
        self.assertEqual(DraftReply.objects.count(), 0)
