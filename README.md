# Researcher Agent Dashboard

A local Python-based researcher agent that:
- fetches technical URL sources and article lists
- extracts unique article URLs
- summarizes articles using Anthropic/Claude
- stores daily history in JSON
- generates a static HTML newsletter and timeline UI

## Setup

1. Install dependencies:

```bash
python -m pip install -e .
```

2. Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your_api_key"
```

If you use keyword search, set a supported search engine API key too:

```bash
export TAVILY_API_KEY="your_tavily_key"
# or
export BING_SEARCH_API_KEY="your_bing_key"
# or
export SERPAPI_API_KEY="your_serpapi_key"
```

Tavily is a recommended provider with a free tier for up to 1,000 searches per month.

## Usage

Run the CLI with one or more source URLs:

```bash
researcher-dashboard --url https://example.com/blog --url https://example.com/research
```

Or provide a file with one URL per line:

```bash
researcher-dashboard --source-file sources.txt
```

Or provide a file of content search seeds and use a search engine provider to discover article URLs:

```bash
researcher-dashboard --search-file content_search_seeds.txt --search-provider tavily
```

Tavily is a good choice for autonomous-agent search with a generous free tier.

## Output

- `data/index.json` — log of run dates and metadata
- `data/daily/YYYY-MM-DD.json` — newsletter items for each day
- `output/index.html` — static timeline UI
- `output/newsletter-YYYY-MM-DD.html` — archived newsletter pages

## Notes

- The newsletter is limited to 10 unique articles per day.
- Articles already included in previous newsletters are filtered out.
- The timeline UI loads historic newsletters by date.
