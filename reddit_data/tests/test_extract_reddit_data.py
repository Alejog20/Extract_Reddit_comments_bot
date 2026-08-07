from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from reddit_data.models import Comment, RedditPost

TOKEN_RESPONSE = {"access_token": "fake-token"}

SEARCH_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "post1",
                    "title": "Struggling with lead gen",
                    "selftext": "Any advice?",
                    "subreddit": "sales",
                    "score": 12,
                    "upvote_ratio": 0.88,
                    "num_comments": 1,
                    "permalink": "/r/sales/comments/post1/",
                    "created_utc": 1700000000,
                }
            }
        ]
    }
}

COMMENTS_RESPONSE = [
    {},
    {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "comment1",
                        "body": "Try cold email",
                        "score": 3,
                        "author": "helper",
                        "permalink": "/r/sales/comments/post1/comment1/",
                    }
                }
            ]
        }
    },
]


class FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data
        self.text = ""

    def json(self):
        return self._json_data


@override_settings()
class ExtractRedditDataCommandTests(TestCase):
    def test_missing_credentials_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CommandError):
                call_command(
                    "extract_reddit_data",
                    terms="lead gen",
                    subreddits="sales",
                    stdout=StringIO(),
                )

    @patch("reddit_data.management.commands.extract_reddit_data.requests.get")
    @patch("reddit_data.management.commands.extract_reddit_data.requests.post")
    def test_extraction_creates_post_and_comment(self, mock_post, mock_get):
        mock_post.return_value = FakeResponse(200, TOKEN_RESPONSE)
        mock_get.side_effect = [
            FakeResponse(200, SEARCH_RESPONSE),
            FakeResponse(200, COMMENTS_RESPONSE),
        ]

        with patch.dict(
            "os.environ",
            {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "secret"},
        ), patch("time.sleep", return_value=None):
            call_command(
                "extract_reddit_data",
                terms="lead gen",
                subreddits="sales",
                stdout=StringIO(),
            )

        self.assertEqual(RedditPost.objects.count(), 1)
        post = RedditPost.objects.get(post_id="post1")
        self.assertEqual(post.subreddit, "sales")
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.get(comment_id="comment1")
        self.assertEqual(comment.post, post)

    @patch("reddit_data.management.commands.extract_reddit_data.requests.get")
    @patch("reddit_data.management.commands.extract_reddit_data.requests.post")
    def test_rerun_does_not_duplicate_posts(self, mock_post, mock_get):
        mock_post.return_value = FakeResponse(200, TOKEN_RESPONSE)
        mock_get.side_effect = [
            FakeResponse(200, SEARCH_RESPONSE),
            FakeResponse(200, COMMENTS_RESPONSE),
            FakeResponse(200, SEARCH_RESPONSE),
            FakeResponse(200, COMMENTS_RESPONSE),
        ]

        with patch.dict(
            "os.environ",
            {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "secret"},
        ), patch("time.sleep", return_value=None):
            call_command("extract_reddit_data", terms="lead gen", subreddits="sales", stdout=StringIO())
            call_command("extract_reddit_data", terms="lead gen", subreddits="sales", stdout=StringIO())

        self.assertEqual(RedditPost.objects.count(), 1)
