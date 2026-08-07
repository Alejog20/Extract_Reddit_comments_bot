from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

from .models import AnalysisResult

TOP_PAIN_POINTS_LIMIT = 15
TIME_TREND_LIMIT = 50


def top_pain_points():
    """Most frequent exact pain-point strings, most common first."""
    return list(
        AnalysisResult.objects.exclude(pain_point="")
        .values("pain_point")
        .annotate(count=Count("id"))
        .order_by("-count", "pain_point")[:TOP_PAIN_POINTS_LIMIT]
    )


def subreddit_intent_ranking():
    """Subreddits ranked by how many high-intent posts they've produced."""
    rows = list(
        AnalysisResult.objects.values("post__subreddit")
        .annotate(
            high_intent_count=Count("id", filter=Q(is_high_intent=True)),
            total_analyzed=Count("id"),
        )
        .order_by("-high_intent_count", "-total_analyzed")
    )
    for row in rows:
        row["subreddit"] = row.pop("post__subreddit")
        row["high_intent_rate"] = (
            round(100 * row["high_intent_count"] / row["total_analyzed"], 1)
            if row["total_analyzed"]
            else 0
        )
    return rows


def high_intent_trend_by_month():
    """High-intent post counts per subreddit per month, most recent first."""
    rows = list(
        AnalysisResult.objects.filter(is_high_intent=True)
        .annotate(month=TruncMonth("post__created_utc"))
        .values("month", "post__subreddit")
        .annotate(count=Count("id"))
        .order_by("-month", "-count")[:TIME_TREND_LIMIT]
    )
    for row in rows:
        row["subreddit"] = row.pop("post__subreddit")
    return rows
