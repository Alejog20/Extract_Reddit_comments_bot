from django.test import TestCase
from django.utils import timezone

from reddit_data.models import AnalysisResult, Comment, DraftReply, RedditPost


class RedditPostModelTests(TestCase):
    def test_create_post_and_str(self):
        post = RedditPost.objects.create(
            post_id="abc123",
            title="Struggling with cold outreach",
            text="Anyone got tips?",
            subreddit="sales",
            score=10,
            upvote_ratio=0.9,
            num_comments=2,
            permalink="https://www.reddit.com/r/sales/comments/abc123/",
            search_term="cold outreach",
            created_utc=timezone.now(),
        )
        self.assertEqual(RedditPost.objects.count(), 1)
        self.assertIn("sales", str(post))

    def test_post_id_must_be_unique(self):
        RedditPost.objects.create(
            post_id="dup1",
            title="First",
            subreddit="sales",
            permalink="https://www.reddit.com/r/sales/comments/dup1/",
            search_term="term",
            created_utc=timezone.now(),
        )
        with self.assertRaises(Exception):
            RedditPost.objects.create(
                post_id="dup1",
                title="Second",
                subreddit="sales",
                permalink="https://www.reddit.com/r/sales/comments/dup1/",
                search_term="term",
                created_utc=timezone.now(),
            )


class CommentModelTests(TestCase):
    def setUp(self):
        self.post = RedditPost.objects.create(
            post_id="post1",
            title="Post with comments",
            subreddit="marketing",
            permalink="https://www.reddit.com/r/marketing/comments/post1/",
            search_term="term",
            created_utc=timezone.now(),
        )

    def test_create_comment_linked_to_post(self):
        comment = Comment.objects.create(
            post=self.post,
            comment_id="c1",
            text="This is a comment",
            score=5,
            author="someuser",
            permalink="https://www.reddit.com/r/marketing/comments/post1/c1/",
        )
        self.assertEqual(self.post.comments.count(), 1)
        self.assertEqual(comment.post, self.post)

    def test_deleting_post_cascades_to_comments(self):
        Comment.objects.create(
            post=self.post,
            comment_id="c2",
            text="Another comment",
            permalink="https://www.reddit.com/r/marketing/comments/post1/c2/",
        )
        self.post.delete()
        self.assertEqual(Comment.objects.filter(comment_id="c2").count(), 0)


class AnalysisResultModelTests(TestCase):
    def setUp(self):
        self.post = RedditPost.objects.create(
            post_id="post2",
            title="Need a better CRM",
            subreddit="sales",
            permalink="https://www.reddit.com/r/sales/comments/post2/",
            search_term="crm",
            created_utc=timezone.now(),
        )

    def test_create_analysis_linked_to_post(self):
        analysis = AnalysisResult.objects.create(
            post=self.post,
            pain_point="Current CRM is too slow",
            sentiment="negative",
            is_high_intent=True,
        )
        self.assertEqual(self.post.analysis, analysis)
        self.assertIn("post2", str(analysis))

    def test_post_can_have_only_one_analysis(self):
        AnalysisResult.objects.create(post=self.post, sentiment="neutral")
        with self.assertRaises(Exception):
            AnalysisResult.objects.create(post=self.post, sentiment="positive")


class DraftReplyModelTests(TestCase):
    def setUp(self):
        self.post = RedditPost.objects.create(
            post_id="post3",
            title="Looking for outreach tools",
            subreddit="marketing",
            permalink="https://www.reddit.com/r/marketing/comments/post3/",
            search_term="outreach",
            created_utc=timezone.now(),
        )

    def test_draft_defaults_to_pending(self):
        draft = DraftReply.objects.create(post=self.post, proposed_text="Have you tried X?")
        self.assertEqual(draft.status, "pending")
        self.assertIsNone(draft.reviewed_at)

    def test_post_can_have_multiple_drafts(self):
        DraftReply.objects.create(post=self.post, proposed_text="Draft one")
        DraftReply.objects.create(post=self.post, proposed_text="Draft two")
        self.assertEqual(self.post.drafts.count(), 2)
