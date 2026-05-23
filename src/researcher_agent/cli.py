import argparse
import json
import logging
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv

from .agent import ClaudeAgent
from .article import ArticleRecord
from .config import (
    DEFAULT_DOMAIN_BOOST,
    DEFAULT_DOMAIN_MODE,
    DEFAULT_EXCLUDE_DOMAINS,
    DEFAULT_KEYWORDS,
    DEFAULT_MAX_ARTICLES,
    DEFAULT_PREFERRED_DOMAINS_FILE,
)
from .dashboard import generate_index_page, generate_newsletter_page
from .email_delivery import send_newsletter
from .fetcher import fetch_html
from .minhash import compute_signature, is_near_duplicate
from .parser import extract_candidate_urls, extract_article_metadata
from .ranker import filter_new_articles, select_top_articles
from .search_engine import load_search_terms, search_for_terms
from .storage import get_history, update_history, update_index, save_daily_run
from .utils import ensure_directories, load_domain_list, normalize_title

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a technical research newsletter from source URLs.")
    parser.add_argument("--url", "-u", action="append", help="Source URL to collect articles from.")
    parser.add_argument("--source-file", "-f", help="Path to a text file containing one URL per line.")
    parser.add_argument("--search-file", help="Path to a text file containing one search keyword per line.")
    parser.add_argument("--search-provider", choices=["bing", "serpapi", "tavily"], help="Search engine provider to query for keywords.")
    parser.add_argument("--search-api-key", help="Optional search engine API key; falls back to environment variables.")
    parser.add_argument("--search-max-results", type=int, default=20, help="Maximum number of search results to retrieve per keyword. Larger values give dedup more headroom.")
    parser.add_argument("--keywords", "-k", nargs="*", help="Optional keywords for relevance guidance.")
    parser.add_argument("--max-articles", type=int, default=DEFAULT_MAX_ARTICLES, help="Maximum number of articles to include in the newsletter.")
    parser.add_argument("--dedup-days", type=int, default=60, help="Only dedup against articles included in the last N days; older articles may resurface.")
    parser.add_argument("--min-articles", type=int, default=3, help="Warn if fewer than this many articles end up selected for the day.")
    parser.add_argument("--max-content-chars", type=int, default=6000, help="Truncate article content to this many characters before sending to Claude. 0 disables. Default keeps cost predictable; first ~6k chars almost always contain the thesis.")
    parser.add_argument("--max-per-domain", type=int, default=2, help="Cap the number of selected articles per source domain. Forces diversity. Set to 0 to disable.")
    parser.add_argument("--exclude-domain", action="append", help="Skip search results from this domain (repeat to add multiple). Defaults to known scraping-blockers like medium.com.")
    parser.add_argument("--email-to", help="If set, email the rendered newsletter to this address via SMTP. Requires SMTP_USER and SMTP_APP_PASSWORD in .env.")
    parser.add_argument("--preferred-domains", default=DEFAULT_PREFERRED_DOMAINS_FILE, help="Path to a text file with one preferred domain per line (#-comments allowed).")
    parser.add_argument("--domain-mode", choices=["off", "strict", "boost"], default=DEFAULT_DOMAIN_MODE,
                        help="How to use the preferred-domains list. strict: restrict Tavily search to these domains only. boost: rank in-list articles higher. off: ignore the list.")
    parser.add_argument("--domain-boost", type=float, default=DEFAULT_DOMAIN_BOOST, help="Multiplier applied to relevance_score for in-list articles when --domain-mode=boost.")
    parser.add_argument("--request-delay-seconds", type=float, default=4.0, help="Sleep this many seconds between Claude annotation calls to stay under rate limits. 0 disables.")
    parser.add_argument("--failure-backoff-seconds", type=float, default=30.0, help="When 3+ Claude calls fail in a row, sleep this long before continuing. Lets transient overload clear.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and score articles without writing output files.")
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()
    source_urls = set(args.url or [])
    if args.source_file:
        with open(args.source_file, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    source_urls.add(line)

    search_terms = []
    search_results = []
    preferred_domains = []
    if args.search_file:
        search_terms = load_search_terms(args.search_file)
        if not search_terms:
            logger.error("Search file %s contains no keywords.", args.search_file)
            raise SystemExit(1)
        exclude_domains = args.exclude_domain if args.exclude_domain is not None else DEFAULT_EXCLUDE_DOMAINS
        if exclude_domains:
            logger.info("Excluding domains from search: %s", ", ".join(exclude_domains))
        preferred_domains = load_domain_list(args.preferred_domains) if args.domain_mode != "off" else []
        include_domains_arg = preferred_domains if args.domain_mode == "strict" else None
        if preferred_domains:
            logger.info(
                "Preferred-domains mode=%s, %d domains loaded from %s",
                args.domain_mode, len(preferred_domains), args.preferred_domains,
            )
        search_results = search_for_terms(
            args.search_file,
            provider=args.search_provider,
            api_key=args.search_api_key,
            max_results=args.search_max_results,
            exclude_domains=exclude_domains,
            include_domains=include_domains_arg,
        )

    if not source_urls and not search_terms:
        logger.error("No source URLs or search keywords provided. Use --url, --source-file, or --search-file.")
        raise SystemExit(1)

    keywords = args.keywords or DEFAULT_KEYWORDS
    ensure_directories()

    history = get_history()
    cutoff_date = (datetime.utcnow() - timedelta(days=args.dedup_days)).strftime("%Y-%m-%d")
    window_articles = [
        article for article in history.get("articles", {}).values()
        if (article.get("last_included") or "") >= cutoff_date
    ]
    seen_urls = {article["url"] for article in window_articles if article.get("url")}
    seen_titles = {
        normalize_title(article.get("title"))
        for article in window_articles
        if article.get("title")
    }
    seen_titles.discard("")
    history_signatures = [
        article["minhash"] for article in window_articles if article.get("minhash")
    ]
    logger.info(
        "Dedup window: last %d days (cutoff %s). %d historical articles in window.",
        args.dedup_days, cutoff_date, len(window_articles),
    )
    run_titles = set()
    run_signatures = []

    agent = ClaudeAgent(max_content_chars=args.max_content_chars)
    articles = []
    candidate_sources = {}
    consecutive_failures = 0
    SEQ_FAIL_THRESHOLD = 3

    for source_url in sorted(source_urls):
        logger.info("Fetching source: %s", source_url)
        html = fetch_html(source_url)
        candidates = extract_candidate_urls(source_url, html)
        if not candidates:
            candidates = {source_url}
        for candidate in sorted(candidates):
            candidate_sources.setdefault(candidate, source_url)

    for term, result_url in search_results:
        candidate_sources.setdefault(result_url, term)

    for candidate in sorted(candidate_sources):
        if candidate in seen_urls:
            logger.info("Skipping already seen article: %s", candidate)
            continue
        article_html = fetch_html(candidate)
        metadata = extract_article_metadata(candidate, article_html)
        if not metadata:
            continue
        title_key = normalize_title(metadata.get("title"))
        if title_key and (title_key in seen_titles or title_key in run_titles):
            logger.info("Skipping duplicate-title article: %s", candidate)
            continue
        signature = compute_signature(metadata.get("content"))
        if signature and (
            is_near_duplicate(signature, history_signatures)
            or is_near_duplicate(signature, run_signatures)
        ):
            logger.info("Skipping near-duplicate article: %s", candidate)
            continue
        if title_key:
            run_titles.add(title_key)
        if signature:
            run_signatures.append(signature)
        metadata["source_url"] = candidate_sources.get(candidate)
        try:
            annotation = agent.annotate_article(metadata)
            consecutive_failures = 0
        except Exception as exc:
            consecutive_failures += 1
            logger.warning("Skipping %s — annotation failed: %s", candidate, exc)
            if consecutive_failures >= SEQ_FAIL_THRESHOLD and args.failure_backoff_seconds > 0:
                extra = max(args.failure_backoff_seconds - args.request_delay_seconds, 0)
                if extra > 0:
                    logger.warning("%d consecutive failures — sleeping %.0fs before continuing", consecutive_failures, extra)
                    time.sleep(extra)
            if args.request_delay_seconds > 0:
                time.sleep(args.request_delay_seconds)
            continue
        article = ArticleRecord(
            url=candidate,
            title=metadata.get("title", candidate),
            author=metadata.get("author"),
            published_at=metadata.get("published_at"),
            summary=annotation.get("summary"),
            content=metadata.get("content"),
            category=annotation.get("category", "other"),
            relevance_score=float(annotation.get("relevance_score", 0.0)),
            tags=annotation.get("tags", []),
            takeaways=annotation.get("takeaways") or [],
            first_seen=datetime.utcnow().strftime("%Y-%m-%d"),
            source_url=metadata.get("source_url"),
            minhash=signature,
        )
        articles.append(article)
        if args.request_delay_seconds > 0:
            time.sleep(args.request_delay_seconds)

    articles = filter_new_articles(articles, seen_urls)
    boost_domains = preferred_domains if args.search_file and args.domain_mode == "boost" else None
    selected = select_top_articles(
        articles,
        args.max_articles,
        preferred_domains=boost_domains,
        boost=args.domain_boost,
        max_per_domain=args.max_per_domain,
    )
    run_date = datetime.utcnow().strftime("%Y-%m-%d")

    if len(selected) < args.min_articles:
        logger.warning(
            "Only %d article(s) selected for %s (threshold %d). "
            "Consider widening seeds, increasing --search-max-results, or shortening --dedup-days.",
            len(selected), run_date, args.min_articles,
        )

    if args.dry_run:
        logger.info("Dry run: selected %d articles", len(selected))
        logger.info(json.dumps([article.to_dict() for article in selected], indent=2, ensure_ascii=False))
        return

    source_inputs = sorted(source_urls) + [f"search:{term}" for term in search_terms]

    overview = None
    if selected:
        try:
            overview = agent.summarize_day(selected)
        except Exception as exc:
            logger.warning("Daily overview generation failed (%s) — saving without one.", exc)
    if overview:
        logger.info("Daily overview: %s", overview)

    save_daily_run(run_date, selected, source_inputs)
    update_history(selected, run_date)
    index = update_index(run_date, source_inputs, len(selected), f"newsletter-{run_date}.html", overview=overview)
    generate_newsletter_page(run_date, selected, index)
    generate_index_page(index)
    logger.info("Newsletter written for %s with %d articles.", run_date, len(selected))

    if args.email_to and selected:
        try:
            send_newsletter(run_date, selected, overview, args.email_to)
        except Exception as exc:
            logger.error("Failed to send newsletter email to %s: %s", args.email_to, exc)
