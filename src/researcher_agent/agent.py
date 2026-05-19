import json
import logging
import os

import anthropic

from .config import ANTHROPIC_API_KEY_ENV, DEFAULT_MODEL

logger = logging.getLogger(__name__)

ANNOTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["blog", "research", "news", "tutorial", "opinion", "other"],
        },
        "relevance_score": {"type": "number"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "category", "relevance_score", "tags"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are a research newsletter editor. "
    "Given an article's title, source, author, published date, and content, return JSON with these fields:\n"
    "- summary: a newsletter summary of up to 300 words. Aim for one or two paragraphs that capture the article's thesis, key findings or arguments, and why a technical reader should care. Do not exceed 300 words.\n"
    "- category: one of blog, research, news, tutorial, opinion, other.\n"
    "- relevance_score: number between 0.0 and 1.0, where 1.0 means highly relevant to technical research, developer tools, AI, or software engineering.\n"
    "- tags: a list of up to three short topic tags.\n"
    "If the content is not relevant to those topics, choose a relevance_score near 0.0."
)


class ClaudeAgent:
    def __init__(self, api_key=None, model=None, max_content_chars=12000):
        api_key = api_key or os.environ.get(ANTHROPIC_API_KEY_ENV)
        if not api_key:
            raise EnvironmentError(f"Missing {ANTHROPIC_API_KEY_ENV} environment variable")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODEL
        self.max_content_chars = max_content_chars or 0

    def annotate_article(self, metadata):
        user_message = self._build_user_message(metadata)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": ANNOTATION_SCHEMA,
                }
            },
        )
        text = next((block.text for block in response.content if block.type == "text"), "")
        return self._parse_response(text)

    def _build_user_message(self, metadata):
        title = metadata.get("title", "")
        source = metadata.get("source_url", "")
        author = metadata.get("author", "")
        published_at = metadata.get("published_at", "")
        content = metadata.get("content", "") or ""
        if self.max_content_chars and len(content) > self.max_content_chars:
            logger.info(
                "Truncating content for annotation: %d -> %d chars (%s)",
                len(content), self.max_content_chars, title[:80],
            )
            content = content[: self.max_content_chars].rstrip() + "\n\n[…content truncated for length]"
        return (
            f"Title: {title}\n"
            f"Source: {source}\n"
            f"Author: {author}\n"
            f"Published: {published_at}\n"
            f"Content:\n{content}"
        )

    def summarize_day(self, articles):
        if not articles:
            return None
        bullets = []
        for article in articles[:20]:
            title = (article.title or "Untitled").strip()
            summary = (article.summary or "").strip()
            bullets.append(f"- {title}\n  {summary}")
        body = "\n\n".join(bullets)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            system=(
                "You are a research newsletter editor. Given the titles and summaries of today's selected articles, "
                "write a TL;DR overview in 1-2 short sentences, no more than 40 words total. "
                "Name the main thread or theme; mention at most one concrete concept or finding worth highlighting. "
                "Plain prose only — no markdown, no bold, no parenthetical enumerations, no em-dash lists. "
                "Do not greet the reader, do not sign off, do not use the word 'today'. "
                "Return only the overview text."
            ),
            messages=[{"role": "user", "content": f"Articles:\n\n{body}"}],
        )
        text = next((block.text for block in response.content if block.type == "text"), "").strip()
        return text or None

    def _parse_response(self, text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Claude returned invalid JSON: %s", text)
            return {
                "summary": None,
                "category": "other",
                "relevance_score": 0.0,
                "tags": [],
            }
