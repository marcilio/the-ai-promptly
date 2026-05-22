from typing import List, Optional

from .article import ArticleRecord
from .utils import url_in_domains


def _effective_score(article: ArticleRecord, preferred_domains: Optional[List[str]], boost: float) -> float:
    base = article.relevance_score
    if preferred_domains and url_in_domains(article.url, preferred_domains):
        return base * boost
    return base


def select_top_articles(
    articles: List[ArticleRecord],
    max_articles: int,
    preferred_domains: Optional[List[str]] = None,
    boost: float = 1.0,
):
    filtered = [article for article in articles if article.relevance_score > 0.0]
    sorted_articles = sorted(
        filtered,
        key=lambda item: (
            _effective_score(item, preferred_domains, boost),
            item.published_at or "",
            item.first_seen or "",
        ),
        reverse=True,
    )
    return sorted_articles[:max_articles]


def filter_new_articles(articles: List[ArticleRecord], history_urls):
    return [article for article in articles if article.url not in history_urls]
