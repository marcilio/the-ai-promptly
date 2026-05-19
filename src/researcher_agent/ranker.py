from typing import List

from .article import ArticleRecord


def select_top_articles(articles: List[ArticleRecord], max_articles: int):
    filtered = [article for article in articles if article.relevance_score > 0.0]
    sorted_articles = sorted(
        filtered,
        key=lambda item: (item.relevance_score, item.published_at or "", item.first_seen or ""),
        reverse=True,
    )
    return sorted_articles[:max_articles]


def filter_new_articles(articles: List[ArticleRecord], history_urls):
    return [article for article in articles if article.url not in history_urls]
