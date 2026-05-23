from typing import List, Optional

from .article import ArticleRecord
from .utils import url_hostname, url_in_domains


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
    max_per_domain: Optional[int] = None,
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

    if not max_per_domain or max_per_domain <= 0:
        return sorted_articles[:max_articles]

    selected: List[ArticleRecord] = []
    overflow: List[ArticleRecord] = []
    counts = {}
    for article in sorted_articles:
        host = url_hostname(article.url)
        if counts.get(host, 0) < max_per_domain:
            selected.append(article)
            counts[host] = counts.get(host, 0) + 1
            if len(selected) >= max_articles:
                return selected
        else:
            overflow.append(article)
    # Diversity exhausted before hitting max_articles → top up from overflow
    if len(selected) < max_articles:
        selected.extend(overflow[: max_articles - len(selected)])
    return selected


def filter_new_articles(articles: List[ArticleRecord], history_urls):
    return [article for article in articles if article.url not in history_urls]
