import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .utils import extract_text_nodes, humanize_url_slug, normalize_url

ARTICLE_PATH_HINTS = ["article", "blog", "post", "paper", "research", "news", "note"]


def is_likely_article_page(html):
    if not html:
        return False
    lower = html.lower()
    if "<article" in lower or "article:published_time" in lower:
        return True
    return False


def extract_candidate_urls(source_url, html):
    candidates = set()
    if not html:
        return candidates
    if is_likely_article_page(html):
        candidates.add(source_url)
        return candidates

    soup = BeautifulSoup(html, "html.parser")
    for element in soup.find_all("a", href=True):
        if element["href"].startswith("mailto:"):
            continue
        href = normalize_url(element["href"], base=source_url)
        if not href:
            continue
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue
        if href == source_url:
            continue
        if _looks_like_article_link(element, href, source_url):
            candidates.add(href)
    return candidates


def _looks_like_article_link(element, href, source_url):
    if href.startswith(source_url) or urlparse(href).netloc == urlparse(source_url).netloc:
        path = urlparse(href).path.lower()
        if any(hint in path for hint in ARTICLE_PATH_HINTS):
            return True
        anchor = (element.get_text(" ") or "").strip().lower()
        if len(anchor) > 12 and ("read" in anchor or "article" in anchor or "post" in anchor):
            return True
        if element.find_parent("article") is not None:
            return True
    return False


def extract_article_metadata(url, html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    title = _get_title(soup) or humanize_url_slug(url)
    summary = _get_summary(soup)
    author = _get_author(soup)
    published_at = _get_published_date(soup)
    content = _extract_main_text(soup)
    return {
        "url": url,
        "title": title or url,
        "summary": summary,
        "author": author,
        "published_at": published_at,
        "content": extract_text_nodes(content),
    }


_TITLE_META_SELECTORS = [
    {"property": "og:title"},
    {"name": "og:title"},
    {"property": "twitter:title"},
    {"name": "twitter:title"},
    {"name": "citation_title"},
    {"name": "dc.title"},
    {"name": "DC.title"},
    {"itemprop": "headline"},
    {"itemprop": "name"},
]


def _get_title(soup):
    for selector in _TITLE_META_SELECTORS:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            text = tag["content"].strip()
            if text:
                return text
    if soup.title and soup.title.string:
        text = soup.title.string.strip()
        if text:
            return text
    heading = soup.find(re.compile("^h[1-3]$"))
    if heading:
        text = heading.get_text(strip=True)
        if text:
            return text
    return None


def _get_summary(soup):
    summary_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if summary_tag:
        return summary_tag.get("content", "").strip()
    return None


_AUTHOR_MAX_CHARS = 500
_AUTHOR_META_SELECTORS = [
    {"name": "author"},
    {"property": "article:author"},
    {"name": "citation_author"},
    {"name": "dc.creator"},
    {"name": "DC.Creator"},
    {"name": "byl"},
]


def _get_author(soup):
    for selector in _AUTHOR_META_SELECTORS:
        tags = soup.find_all("meta", attrs=selector)
        if tags:
            joined = ", ".join(t.get("content", "").strip() for t in tags if t.get("content"))
            if joined:
                return joined[:_AUTHOR_MAX_CHARS] if len(joined) <= _AUTHOR_MAX_CHARS else None

    # Narrowed selectors: prefer schema-org / common explicit author markup, not just
    # any element with "author" in its class name (which on arxiv html pages can wrap
    # the entire paper body).
    for selector in [
        "[itemprop=author]",
        "[rel=author]",
        ".author-name",
        ".byline-author",
        ".byline",
        ".post-author",
        ".article-author",
        ".authors",
    ]:
        match = soup.select_one(selector)
        if match:
            text = match.get_text(" ", strip=True)
            if text and len(text) <= _AUTHOR_MAX_CHARS:
                return text
    return None


_DATE_META_SELECTORS = [
    {"property": "article:published_time"},
    {"property": "og:published_time"},
    {"property": "og:article:published_time"},
    {"name": "date"},
    {"name": "pubdate"},
    {"name": "publish-date"},
    {"name": "publication-date"},
    {"name": "publication_date"},
    {"name": "dc.date"},
    {"name": "dc.date.issued"},
    {"name": "DC.date.issued"},
    {"itemprop": "datePublished"},
    {"name": "citation_publication_date"},
    {"name": "sailthru.date"},
    {"name": "parsely-pub-date"},
]


def _get_published_date(soup):
    for selector in _DATE_META_SELECTORS:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            return tag["content"].strip()

    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag and time_tag.get("datetime"):
        return time_tag["datetime"].strip()
    time_tag = soup.find("time")
    if time_tag:
        text = time_tag.get_text(" ", strip=True)
        if text:
            return text

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            for key in ("datePublished", "dateCreated", "uploadDate"):
                value = entry.get(key)
                if value:
                    return str(value).strip()

    return None


def _extract_main_text(soup):
    article = soup.find("article")
    if article:
        return article.get_text(separator=" ", strip=True)
    candidates = soup.select("main, .article-content, .post-content, .blog-post, .entry-content")
    if candidates:
        return "\n\n".join([candidate.get_text(separator=" ", strip=True) for candidate in candidates])
    paragraphs = soup.find_all("p")
    return "\n\n".join([p.get_text(strip=True) for p in paragraphs])
