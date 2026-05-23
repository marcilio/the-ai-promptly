import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .config import BASE_DIR, DATA_DIR, OUTPUT_DIR, DAILY_DIR, INDEX_FILE, HISTORY_FILE

TRACKING_PARAM_PREFIXES = ("utm_", "hsa_", "vero_", "mc_", "_hs", "ic_")
TRACKING_PARAMS = frozenset({
    "gclid", "fbclid", "dclid", "msclkid", "yclid", "twclid", "ttclid", "igshid",
    "_ga", "_gl", "ref", "ref_src", "ref_url", "hscta_tracking", "hsctatracking",
    "spm", "share", "share_source", "share_id",
})


def _is_tracking_param(key):
    lower = key.lower()
    if lower in TRACKING_PARAMS:
        return True
    return any(lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)


def ensure_directories():
    for path in [DATA_DIR, OUTPUT_DIR, DAILY_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_url(url, base=None):
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        return None
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[: -len(":80")]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[: -len(":443")]
    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    if parsed.query:
        kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not _is_tracking_param(k)]
        kept.sort()
        query = urlencode(kept)
    else:
        query = ""
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def normalize_title(title):
    if not title:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def load_domain_list(path):
    p = Path(path)
    if not p.exists():
        return []
    domains = []
    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            domains.append(stripped.lower())
    return domains


def url_in_domains(url, domains):
    if not url or not domains:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if host.startswith("www."):
        host = host[4:]
    domain_set = {d[4:] if d.startswith("www.") else d for d in domains}
    return any(host == d or host.endswith("." + d) for d in domain_set)


def url_hostname(url):
    if not url:
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


_KNOWN_ACRONYMS = {
    "ai", "ml", "llm", "llms", "nlp", "rag", "mcp", "api", "apis", "sdk", "cli",
    "ui", "ux", "ide", "os", "io", "gpu", "gpus", "cpu", "tpu", "rl", "ir",
    "html", "css", "json", "xml", "yaml", "sql", "aws", "gcp", "gpt", "etl",
    "iot", "faq", "https", "http", "tcp", "udp", "rest", "ci", "cd", "vm",
    "saas", "paas", "iaas", "pdf", "p2p", "qa", "sre",
}


def humanize_url_slug(url):
    """Turn a URL's last meaningful path segment into a readable title.

    Examples:
      https://example.com/posts/why-it-matters       -> 'Why It Matters'
      https://resources.example.com/hubfs/Some%20PDF.pdf -> 'Some PDF'
      https://arxiv.org/abs/2501.12345v2             -> None  (no human slug)
    """
    from urllib.parse import unquote
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        return None
    slug = unquote(path.rsplit("/", 1)[-1])
    slug = re.sub(r"\.(html?|php|aspx?|jsp|md|pdf|txt)$", "", slug, flags=re.I)
    # arxiv-style version suffix
    slug = re.sub(r"v\d+$", "", slug)
    # If slug is mostly digits / hyphens (e.g. arxiv IDs), skip
    if re.fullmatch(r"[\d\.\-_v]+", slug):
        return None
    cleaned = re.sub(r"[-_+]+", " ", slug).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned or len(cleaned) < 3:
        return None
    words = []
    for w in cleaned.split():
        lw = w.lower()
        if lw in _KNOWN_ACRONYMS:
            words.append(lw.upper())
        elif w.isupper() and 2 <= len(w) <= 5 and w.isalpha():
            words.append(w)
        else:
            words.append(w[:1].upper() + w[1:])
    return " ".join(words)


def extract_text_nodes(html_text):
    cleaned = re.sub(r"\s+", " ", html_text or "").strip()
    return cleaned


def build_date_key(date_str):
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None
