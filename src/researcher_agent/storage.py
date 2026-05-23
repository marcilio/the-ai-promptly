import json
from datetime import datetime
from pathlib import Path

from .config import DAILY_DIR, HISTORY_FILE, INDEX_FILE
from .utils import load_json, save_json


def load_history():
    history = load_json(HISTORY_FILE, default={"articles": {}})
    if history is None:
        history = {"articles": {}}
    return history


def save_history(history):
    save_json(HISTORY_FILE, history)


def get_history():
    return load_history()


def load_index():
    index = load_json(INDEX_FILE, default={"runs": []})
    if index is None:
        index = {"runs": []}
    return index


def get_index():
    return load_index()


def save_index(index):
    save_json(INDEX_FILE, index)


def save_daily_run(date_key, articles, source_urls):
    record = [article.to_dict() for article in articles]
    daily_file = DAILY_DIR / f"{date_key}.json"
    save_json(daily_file, record)
    return str(daily_file)


def update_history(articles, date_key):
    history = load_history()
    for article in articles:
        existing = history["articles"].get(article.url, {})
        if not existing:
            existing = {
                "url": article.url,
                "title": article.title,
                "author": article.author,
                "published_at": article.published_at,
                "summary": article.summary,
                "content": article.content,
                "category": article.category,
                "tags": article.tags,
                "takeaways": article.takeaways,
                "first_seen": date_key,
                "last_included": date_key,
                "relevance_score": article.relevance_score,
                "source_url": article.source_url,
                "minhash": article.minhash,
            }
        else:
            existing.update(
                {
                    "title": article.title,
                    "author": article.author,
                    "published_at": article.published_at,
                    "summary": article.summary,
                    "content": article.content,
                    "category": article.category,
                    "tags": article.tags,
                    "takeaways": article.takeaways or existing.get("takeaways") or [],
                    "relevance_score": article.relevance_score,
                    "last_included": date_key,
                    "minhash": article.minhash if article.minhash is not None else existing.get("minhash"),
                }
            )
        history["articles"][article.url] = existing
    save_history(history)
    return history


def update_index(date_key, source_urls, count, output_filename, overview=None):
    index = load_index()
    existing = next((item for item in index["runs"] if item["date"] == date_key), None)
    run_data = {
        "date": date_key,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_urls": source_urls,
        "count": count,
        "filename": output_filename,
    }
    if overview:
        run_data["overview"] = overview
    if existing:
        existing.update(run_data)
    else:
        index["runs"].append(run_data)
        index["runs"] = sorted(index["runs"], key=lambda item: item["date"], reverse=True)
    save_index(index)
    return index
