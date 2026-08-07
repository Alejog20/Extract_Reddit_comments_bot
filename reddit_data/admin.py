from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from . import analytics
from .models import AnalysisResult, Comment, DraftReply, RedditPost


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("comment_id", "text", "score", "author", "permalink")
    can_delete = False


class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    extra = 0
    readonly_fields = ("pain_point", "sentiment", "is_high_intent", "analyzed_at")
    can_delete = False


class DraftReplyInline(admin.StackedInline):
    model = DraftReply
    extra = 0
    readonly_fields = ("proposed_text", "created_at", "reviewed_at")
    fields = ("proposed_text", "status", "created_at", "reviewed_at")


@admin.register(RedditPost)
class RedditPostAdmin(admin.ModelAdmin):
    list_display = ("title", "subreddit", "score", "num_comments", "search_term", "created_utc")
    list_filter = ("subreddit", "search_term")
    search_fields = ("title", "text", "post_id")
    readonly_fields = ("extracted_at",)
    inlines = [CommentInline, AnalysisResultInline, DraftReplyInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("comment_id", "post", "author", "score")
    search_fields = ("text", "comment_id")


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("post", "sentiment", "is_high_intent", "analyzed_at")
    list_filter = ("sentiment", "is_high_intent")
    search_fields = ("pain_point", "post__title")


@admin.register(DraftReply)
class DraftReplyAdmin(admin.ModelAdmin):
    list_display = ("post", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("proposed_text", "post__title")


def analytics_dashboard(request):
    context = {
        **admin.site.each_context(request),
        "title": "Analytics",
        "top_pain_points": analytics.top_pain_points(),
        "subreddit_ranking": analytics.subreddit_intent_ranking(),
        "time_trend": analytics.high_intent_trend_by_month(),
    }
    return TemplateResponse(request, "admin/reddit_data/analytics.html", context)


_default_get_urls = admin.site.get_urls


def _get_urls():
    custom_urls = [
        path(
            "analytics/",
            admin.site.admin_view(analytics_dashboard),
            name="reddit_data_analytics",
        ),
    ]
    return custom_urls + _default_get_urls()


admin.site.get_urls = _get_urls
