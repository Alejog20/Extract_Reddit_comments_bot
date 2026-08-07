import base64
import datetime
import logging
import os
import re
import time
from urllib.parse import quote

import requests
from django.core.management.base import BaseCommand, CommandError

from reddit_data.models import Comment, RedditPost

logger = logging.getLogger(__name__)

USER_AGENT = "RedditDataExtractor/1.0"


def get_reddit_token(client_id, client_secret):
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "User-Agent": USER_AGENT,
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        headers=headers,
        data=data,
    )
    if response.status_code != 200:
        logger.error("Error obtaining token: %s", response.status_code)
        return None
    return response.json().get("access_token")


def search_reddit(token, query, subreddit, limit=25, sort="relevance"):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }
    encoded_query = quote(query)

    if subreddit.lower() == "all":
        url = f"https://oauth.reddit.com/search?q={encoded_query}&sort={sort}&limit={limit}"
    else:
        url = f"https://oauth.reddit.com/r/{subreddit}/search?q={encoded_query}&sort={sort}&restrict_sr=1&limit={limit}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error("Search error: %s", response.status_code)
        return []
    return response.json().get("data", {}).get("children", [])


def get_comments(token, post_id, limit=25):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }
    url = f"https://oauth.reddit.com/comments/{post_id}?limit={limit}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error("Error fetching comments: %s", response.status_code)
        return []
    data = response.json()
    if len(data) >= 2:
        return data[1].get("data", {}).get("children", [])
    return []


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\[|\]|\(|\)|\*|#|>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class Command(BaseCommand):
    help = "Search Reddit for posts and comments and store them in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--terms",
            required=True,
            help="Comma-separated search terms, e.g. 'lead gen,cold outreach'",
        )
        parser.add_argument(
            "--subreddits",
            required=True,
            help="Plus-separated subreddits, e.g. 'sales+marketing', or 'all'",
        )
        parser.add_argument("--post-limit", type=int, default=25)
        parser.add_argument("--comment-limit", type=int, default=20)
        parser.add_argument("--sort", default="relevance")

    def handle(self, *args, **options):
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise CommandError(
                "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in the environment (.env)."
            )

        search_terms = [t.strip() for t in options["terms"].split(",") if t.strip()]
        subreddits = [s.strip() for s in options["subreddits"].split("+") if s.strip()]
        post_limit = options["post_limit"]
        comment_limit = options["comment_limit"]
        sort = options["sort"]

        token = get_reddit_token(client_id, client_secret)
        if not token:
            raise CommandError("Failed to authenticate with Reddit. Check your credentials.")

        posts_created = 0
        posts_skipped = 0
        comments_created = 0

        for term in search_terms:
            for subreddit in subreddits:
                self.stdout.write(f"Searching '{term}' in r/{subreddit}...")
                results = search_reddit(token, term, subreddit, limit=post_limit, sort=sort)

                for entry in results:
                    post = entry.get("data", {})
                    post_id = post.get("id")
                    if not post_id:
                        continue

                    reddit_post, created = RedditPost.objects.get_or_create(
                        post_id=post_id,
                        defaults={
                            "title": clean_text(post.get("title", "")),
                            "text": clean_text(post.get("selftext", "")),
                            "subreddit": post.get("subreddit", ""),
                            "score": post.get("score", 0),
                            "upvote_ratio": post.get("upvote_ratio", 0),
                            "num_comments": post.get("num_comments", 0),
                            "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                            "search_term": term,
                            "created_utc": datetime.datetime.fromtimestamp(
                                post.get("created_utc", 0), tz=datetime.timezone.utc
                            ),
                        },
                    )
                    if not created:
                        posts_skipped += 1
                        continue
                    posts_created += 1

                    if post.get("num_comments", 0) > 0:
                        comments = get_comments(token, post_id, limit=comment_limit)
                        for comment_entry in comments:
                            comment = comment_entry.get("data", {})
                            comment_id = comment.get("id")
                            if comment.get("body") is None or comment_id is None:
                                continue

                            _, comment_created = Comment.objects.get_or_create(
                                comment_id=comment_id,
                                defaults={
                                    "post": reddit_post,
                                    "text": clean_text(comment.get("body", "")),
                                    "score": comment.get("score", 0),
                                    "author": comment.get("author", "[deleted]") or "",
                                    "permalink": f"https://www.reddit.com{comment.get('permalink', '')}",
                                },
                            )
                            if comment_created:
                                comments_created += 1

                        time.sleep(1)

                time.sleep(2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Posts created: {posts_created}, skipped (already existed): {posts_skipped}, "
                f"comments created: {comments_created}."
            )
        )
