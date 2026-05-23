import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATES_DIR = BASE_DIR / "templates"
DAILY_DIR = DATA_DIR / "daily"
HISTORY_FILE = DATA_DIR / "articles.json"
INDEX_FILE = DATA_DIR / "index.json"
DEFAULT_MAX_ARTICLES = 10
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
SEARCH_ENGINE_PROVIDER_ENV = "SEARCH_ENGINE_PROVIDER"
BING_SEARCH_API_KEY_ENV = "BING_SEARCH_API_KEY"
SERPAPI_API_KEY_ENV = "SERPAPI_API_KEY"
TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
DEFAULT_SEARCH_PROVIDER = "tavily"
DEFAULT_KEYWORDS = [
    "AI",
    "machine learning",
    "research",
    "software engineering",
    "developer tools",
    "systems",
    "data science",
]
DEFAULT_MODEL = "claude-haiku-4-5"
NEWSLETTER_NAME_ENV = "NEWSLETTER_NAME"
DEFAULT_NEWSLETTER_NAME = "The AI Promptly"
NEWSLETTER_AUTHOR_NAME_ENV = "NEWSLETTER_AUTHOR_NAME"
DEFAULT_NEWSLETTER_AUTHOR_NAME = "Marcilio Mendonca"
NEWSLETTER_AUTHOR_URL_ENV = "NEWSLETTER_AUTHOR_URL"
DEFAULT_NEWSLETTER_AUTHOR_URL = "https://www.linkedin.com/in/marcilio/"


def newsletter_name():
    return os.environ.get(NEWSLETTER_NAME_ENV, DEFAULT_NEWSLETTER_NAME)


def newsletter_author_name():
    return os.environ.get(NEWSLETTER_AUTHOR_NAME_ENV, DEFAULT_NEWSLETTER_AUTHOR_NAME)


def newsletter_author_url():
    return os.environ.get(NEWSLETTER_AUTHOR_URL_ENV, DEFAULT_NEWSLETTER_AUTHOR_URL)
DEFAULT_EXCLUDE_DOMAINS = [
    "medium.com",
    "levelup.gitconnected.com",
    "betterprogramming.pub",
    "towardsdatascience.com",
    "pub.towardsai.net",
]
DEFAULT_PREFERRED_DOMAINS_FILE = "preferred_domains.txt"
DEFAULT_DOMAIN_MODE = "boost"   # one of: "off", "strict", "boost"
DEFAULT_DOMAIN_BOOST = 1.3       # multiply relevance_score for in-list domains
