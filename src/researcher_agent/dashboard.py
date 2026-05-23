from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import (
    OUTPUT_DIR,
    TEMPLATES_DIR,
    newsletter_author_name,
    newsletter_author_url,
    newsletter_base_url,
    newsletter_name,
)


def _hostname(url):
    if not url:
        return ""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def render_template(template_name, context):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["hostname"] = _hostname
    template = env.get_template(template_name)
    return template.render(context)


def write_output(filename, content):
    output_path = OUTPUT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _build_og_description(overview, author_name, max_chars=200):
    """Open Graph description: first chunk of the overview + author credit."""
    base = (overview or "").strip().replace("\n", " ")
    if len(base) > max_chars:
        base = base[: max_chars - 1].rstrip() + "…"
    if author_name:
        # Strip credentials/affiliation for a shorter byline in the OG card
        short = author_name.split(",")[0].strip()
        return f"{base} — Curated by {short}".strip(" —")
    return base


def generate_newsletter_page(date_key, articles, index):
    run = next((r for r in index.get("runs", []) if r.get("date") == date_key), None)
    overview = (run or {}).get("overview")
    base_url = newsletter_base_url()
    page_url = f"{base_url}/newsletter-{date_key}.html" if base_url else ""
    content = render_template(
        "newsletter.html",
        {
            "date_key": date_key,
            "articles": [article.to_dict() for article in articles],
            "run_count": len(articles),
            "index": index,
            "overview": overview,
            "newsletter_name": newsletter_name(),
            "newsletter_author_name": newsletter_author_name(),
            "newsletter_author_url": newsletter_author_url(),
            "newsletter_base_url": base_url,
            "page_url": page_url,
            "og_description": _build_og_description(overview, newsletter_author_name()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )
    filename = f"newsletter-{date_key}.html"
    return write_output(filename, content)


def generate_index_page(index):
    content = render_template(
        "index.html",
        {
            "runs": index.get("runs", []),
            "newsletter_name": newsletter_name(),
            "newsletter_author_name": newsletter_author_name(),
            "newsletter_author_url": newsletter_author_url(),
            "newsletter_base_url": newsletter_base_url(),
        },
    )
    return write_output("index.html", content)
