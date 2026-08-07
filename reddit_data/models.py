from django.db import models


class RedditPost(models.Model):
    post_id = models.CharField(max_length=20, unique=True)
    title = models.TextField()
    text = models.TextField(blank=True)
    subreddit = models.CharField(max_length=100)
    score = models.IntegerField(default=0)
    upvote_ratio = models.FloatField(default=0)
    num_comments = models.IntegerField(default=0)
    permalink = models.URLField()
    search_term = models.CharField(max_length=200)
    created_utc = models.DateTimeField()
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subreddit}: {self.title[:50]}"


class Comment(models.Model):
    post = models.ForeignKey(RedditPost, on_delete=models.CASCADE, related_name="comments")
    comment_id = models.CharField(max_length=20, unique=True)
    text = models.TextField()
    score = models.IntegerField(default=0)
    author = models.CharField(max_length=100, blank=True)
    permalink = models.URLField()

    def __str__(self):
        return f"Comment {self.comment_id} on {self.post.post_id}"


class AnalysisResult(models.Model):
    post = models.OneToOneField(RedditPost, on_delete=models.CASCADE, related_name="analysis")
    pain_point = models.TextField(blank=True)
    sentiment = models.CharField(max_length=20, blank=True)
    is_high_intent = models.BooleanField(default=False)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis of {self.post.post_id}"


class DraftReply(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    post = models.ForeignKey(RedditPost, on_delete=models.CASCADE, related_name="drafts")
    proposed_text = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Draft for {self.post.post_id} ({self.status})"
