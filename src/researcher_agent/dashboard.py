from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import OUTPUT_DIR, TEMPLATES_DIR


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


def generate_newsletter_page(date_key, articles, index):
    run = next((r for r in index.get("runs", []) if r.get("date") == date_key), None)
    overview = (run or {}).get("overview")
    content = render_template(
        "newsletter.html",
        {
            "date_key": date_key,
            "articles": [article.to_dict() for article in articles],
            "run_count": len(articles),
            "index": index,
            "overview": overview,
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
        },
    )
    return write_output("index.html", content)
