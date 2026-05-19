import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from .config import (
    BING_SEARCH_API_KEY_ENV,
    DEFAULT_SEARCH_PROVIDER,
    SEARCH_ENGINE_PROVIDER_ENV,
    SERPAPI_API_KEY_ENV,
    TAVILY_API_KEY_ENV,
)

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"bing", "serpapi", "tavily"}


def load_search_terms(file_path: str) -> List[str]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Search terms file not found: {path}")
    terms = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return terms


def resolve_search_provider(provider: Optional[str] = None) -> str:
    if provider:
        provider_value = provider.strip().lower()
    else:
        provider_value = os.environ.get(SEARCH_ENGINE_PROVIDER_ENV, DEFAULT_SEARCH_PROVIDER).strip().lower()
    if provider_value not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported search provider: {provider_value}")
    return provider_value


def resolve_search_api_key(provider: str, api_key: Optional[str] = None) -> Optional[str]:
    if api_key:
        return api_key
    if provider == "bing":
        return os.environ.get(BING_SEARCH_API_KEY_ENV)
    if provider == "serpapi":
        return os.environ.get(SERPAPI_API_KEY_ENV)
    if provider == "tavily":
        return os.environ.get(TAVILY_API_KEY_ENV)
    return None


def search_for_terms(
    search_file: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    max_results: int = 10,
) -> List[Tuple[str, str]]:
    terms = load_search_terms(search_file)
    if not terms:
        return []

    provider = resolve_search_provider(provider)
    api_key = resolve_search_api_key(provider, api_key)
    if not api_key:
        raise EnvironmentError(
            f"Missing API key for search provider {provider}. "
            f"Set {BING_SEARCH_API_KEY_ENV}, {SERPAPI_API_KEY_ENV}, or {TAVILY_API_KEY_ENV}."
        )

    results: List[Tuple[str, str]] = []
    seen = set()
    for term in terms:
        logger.info("Searching for term: %s", term)
        urls = search_query(term, provider, api_key, max_results)
        for url in urls:
            if url not in seen:
                seen.add(url)
                results.append((term, url))
    return results


def search_query(term: str, provider: str, api_key: str, max_results: int) -> List[str]:
    if provider == "bing":
        return bing_search(term, api_key, max_results)
    if provider == "serpapi":
        return serpapi_search(term, api_key, max_results)
    if provider == "tavily":
        return tavily_search(term, api_key, max_results)
    raise ValueError(f"Unsupported provider: {provider}")


def bing_search(query: str, api_key: str, max_results: int = 10) -> List[str]:
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {
        "q": query,
        "count": max_results,
        "textDecorations": False,
        "textFormat": "Raw",
    }
    response = requests.get(endpoint, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    web_pages = data.get("webPages", {}).get("value", [])
    return [item["url"] for item in web_pages if item.get("url")]


def serpapi_search(query: str, api_key: str, max_results: int = 10) -> List[str]:
    endpoint = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": max_results,
    }
    response = requests.get(endpoint, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    results = data.get("organic_results", [])
    urls = []
    for item in results:
        url = item.get("link") or item.get("url")
        if url:
            urls.append(url)
    return urls


def tavily_search(query: str, api_key: str, max_results: int = 10) -> List[str]:
    endpoint = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    json_body = {
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    response = requests.post(endpoint, headers=headers, json=json_body, timeout=20)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    urls = []
    for item in results:
        url = item.get("url")
        if url:
            urls.append(url)
    return urls
