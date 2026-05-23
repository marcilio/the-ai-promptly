import logging
import re

import requests

from .config import USER_AGENT

logger = logging.getLogger(__name__)


def _canonicalize_url(url):
    """Rewrite known problem URLs to cleaner equivalents before fetching."""
    if not url:
        return url
    # arxiv/html/<id> is a verbose full-paper render with no clean meta tags.
    # arxiv/abs/<id> is the abstract page — clean title, author, abstract via meta tags.
    m = re.match(r"^(https?://arxiv\.org)/html/(.+?)(?:v\d+)?/?$", url)
    if m:
        return f"{m.group(1)}/abs/{m.group(2)}"
    m = re.match(r"^(https?://arxiv\.org)/pdf/(.+?)(?:\.pdf)?(?:v\d+)?/?$", url)
    if m:
        return f"{m.group(1)}/abs/{m.group(2)}"
    return url


def fetch_html(url, timeout=20):
    url = _canonicalize_url(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
