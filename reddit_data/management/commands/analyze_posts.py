import logging
import os

import anthropic
from django.core.management.base import BaseCommand, CommandError

from reddit_data.models import AnalysisResult, DraftReply, RedditPost

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You analyze Reddit posts for a B2B marketing team that is \
listening for pain points and buying intent. For each post you are given \
(with its top comments for context), call submit_analysis with:

- pain_point: the specific problem or frustration the poster describes, in \
their own words where possible. Empty string if there isn't a clear one.
- sentiment: one of "positive", "negative", "neutral", "mixed".
- is_high_intent: true only if the poster shows signs of actively looking \
for a solution (asking for recommendations, comparing tools, mentioning \
budget or timeline) rather than just venting.
- proposed_reply: a draft reply a human could post to this thread, written \
using sound persuasion-science practice rather than generic marketing copy:
  1. Open by mirroring the poster's own language back to them so they feel \
understood — this is the single strongest driver of perceived empathy.
  2. Lead with one genuinely useful, specific piece of advice or \
information before anything else (reciprocity) — the reply must stand on \
its own even if the reader never engages further.
  3. Be concrete and specific rather than using hype or superlative \
language; specificity reads as credible, vague enthusiasm reads as spam.
  4. Do not invent or imply a specific product, company, or claim — no \
product context has been provided. If a soft mention is natural, keep it \
generic ("we've seen teams handle this by...") rather than fabricated.
  5. Close with a low-pressure, curiosity-driven question rather than a \
hard call to action.
  6. Sound like a knowledgeable peer commenting in the subreddit, not an \
ad. Match the subreddit's normal tone and length.

This reply is only ever a suggestion a human will review before deciding \
whether to post it manually — never claim otherwise in the reply text \
itself."""

ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "Submit the pain-point analysis and a proposed reply draft for one Reddit post.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "pain_point": {"type": "string"},
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
            },
            "is_high_intent": {"type": "boolean"},
            "proposed_reply": {"type": "string"},
        },
        "required": ["pain_point", "sentiment", "is_high_intent", "proposed_reply"],
        "additionalProperties": False,
    },
}


def build_user_content(post):
    lines = [
        f"Subreddit: r/{post.subreddit}",
        f"Title: {post.title}",
        f"Post text: {post.text or '(no body text)'}",
        "",
        "Top comments:",
    ]
    comments = post.comments.order_by("-score")[:10]
    if not comments:
        lines.append("(no comments)")
    for comment in comments:
        lines.append(f"- (score {comment.score}) {comment.text}")
    return "\n".join(lines)


def analyze_post(client, post):
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        output_config={"effort": "medium"},
        system=SYSTEM_PROMPT,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "submit_analysis"},
        messages=[{"role": "user", "content": build_user_content(post)}],
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return tool_use.input


class Command(BaseCommand):
    help = "Send unanalyzed Reddit posts to Claude and store pain point, sentiment, intent, and a proposed reply."

    def handle(self, *args, **options):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise CommandError("ANTHROPIC_API_KEY must be set in the environment (.env).")

        client = anthropic.Anthropic()
        posts = RedditPost.objects.filter(analysis__isnull=True)

        analyzed = 0
        failed = 0

        for post in posts:
            try:
                result = analyze_post(client, post)
            except anthropic.APIError as exc:
                logger.error("Claude API error analyzing post %s: %s", post.post_id, exc)
                failed += 1
                continue

            AnalysisResult.objects.create(
                post=post,
                pain_point=result["pain_point"],
                sentiment=result["sentiment"],
                is_high_intent=result["is_high_intent"],
            )
            DraftReply.objects.create(
                post=post,
                proposed_text=result["proposed_reply"],
                status="pending",
            )
            analyzed += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done. Analyzed: {analyzed}, failed: {failed}.")
        )
