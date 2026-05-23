# Daily Agentic

> An opinionated, automated AI-research newsletter — searches the web each
> morning, summarizes with Claude, dedupes aggressively, ships to your inbox
> and a public dashboard.

**Live →** *(set after first Vercel deploy)*

---

## What it does

Every morning the agent:

1. **Searches** Tavily for each seed in `content_search_seeds.txt`.
2. **Restricts** results to a curated allowlist in `preferred_domains.txt`
   (no Medium-network spam) or boosts them in rank (`--domain-mode`).
3. **Dedupes** in three layers before any LLM call — normalized URL,
   normalized title, and a MinHash near-duplicate check on body content. The
   dedup window is rolling (default 60 days) so genuinely evergreen articles
   can resurface.
4. **Annotates** each survivor with Claude Haiku 4.5 via structured outputs:
   a 1-2 paragraph summary, 3-5 short takeaways, a category, a relevance
   score (0.0-1.0), and up to 3 topic tags.
5. **Ranks** by relevance, then enforces source diversity
   (`--max-per-domain`, default 2) so a single domain can't monopolize.
6. **Writes a day overview** — one Claude call that distills the selected
   articles into a 1-2 sentence TL;DR.
7. **Renders** a dark-themed static dashboard with a scrubbable timeline,
   plus a per-day page with Open Graph tags and one-click LinkedIn share.
8. **Sends** an email via Gmail SMTP and **publishes** to Vercel.

Built for personal use; configurable enough to be your own.

---

## Stack

- **Python 3.12** — `anthropic`, `beautifulsoup4`, `jinja2`, `requests`, `python-dotenv`
- **Claude Haiku 4.5** via the Messages API with structured outputs, prompt
  caching, and adaptive retry/backoff for transient 429/529s
- **Tavily** for search (free tier covers ~1k searches/month)
- **Gmail SMTP** for email (App Password, not account password)
- **Static HTML/CSS/JS** dashboard — no framework, no build step beyond
  template rendering
- **launchd** for daily scheduling on macOS
- **Vercel** for hosting

---

## Quick start

```bash
# 1. clone
git clone git@github.com:marcilio/the-ai-promptly.git
cd the-ai-promptly

# 2. python 3.12 env (uv is recommended; venv also works)
uv venv --python 3.12 .venv
.venv/bin/pip install -e .

# 3. configure secrets — edit .env in your terminal, never in chat
cp .env.example .env  # (create this file with the contents below)
```

`.env` contents:

```bash
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...

# Email delivery
SMTP_USER=you@gmail.com
SMTP_APP_PASSWORD=...   # Gmail App Password, not your account password

# Branding (all optional — defaults exist)
NEWSLETTER_NAME="Daily Agentic"
NEWSLETTER_AUTHOR_NAME="Your Name, Title"
NEWSLETTER_AUTHOR_URL="https://www.linkedin.com/in/you/"
NEWSLETTER_BASE_URL="https://your-newsletter.vercel.app"   # after first deploy
```

```bash
# 4. customize what to track — one search query per line
$EDITOR content_search_seeds.txt

# 5. customize which sources you trust — one domain per line, #-comments OK
$EDITOR preferred_domains.txt

# 6. run it
.venv/bin/researcher-dashboard \
    --search-file content_search_seeds.txt \
    --search-provider tavily \
    --domain-mode strict \
    --email-to you@gmail.com
```

Open `output/index.html` (via `python -m http.server` from the project
root → `http://localhost:8000/output/`) to see the dashboard.

---

## Daily schedule (macOS)

A sample plist is in `launchd/`. Customize the paths and email, then:

```bash
mkdir -p ~/Library/Logs ~/Library/LaunchAgents
cp launchd/com.marcilio.frontier-newsletter.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) \
   ~/Library/LaunchAgents/com.marcilio.frontier-newsletter.plist
```

Logs land at `~/Library/Logs/frontier-newsletter.{out,err}.log`. Mac must
be awake at the scheduled time; launchd will catch up on next wake if
asleep.

---

## Publishing

```bash
python scripts/build_dist.py            # packages output/ + data/ into dist/
git add dist
git commit -m "Update $(date +%F)"
git push
```

Vercel watches the repo and auto-deploys `dist/` on every push.

---

## Configuration knobs

| Flag | Default | What it does |
|---|---|---|
| `--search-file` | — | Path to a one-seed-per-line file |
| `--search-provider` | `tavily` | `tavily`, `bing`, or `serpapi` |
| `--search-max-results` | 20 | Candidates returned per seed |
| `--max-articles` | 10 | Final newsletter size after dedup + ranking |
| `--max-per-domain` | 2 | Diversity cap per source domain |
| `--dedup-days` | 60 | Rolling window for cross-day dedup |
| `--min-articles` | 3 | Log a warning if selection is thinner than this |
| `--max-content-chars` | 6000 | Truncate body before sending to Claude |
| `--request-delay-seconds` | 4 | Inter-call pacing to stay under tier ITPM |
| `--failure-backoff-seconds` | 30 | Extra sleep after 3 consecutive Claude failures |
| `--domain-mode` | `boost` | `off` / `strict` / `boost` |
| `--domain-boost` | 1.3 | Score multiplier for in-list domains (boost mode) |
| `--exclude-domain` | (defaults exclude Medium-network sites) | Repeatable |
| `--preferred-domains` | `preferred_domains.txt` | Allowlist file path |
| `--email-to` | — | Send the rendered newsletter to this address |
| `--dry-run` | off | Score + print selection, write no files |

---

## Cost

Typical day at Haiku 4.5 pricing:

| Item | Per run |
|---|---|
| Tavily searches (1 per seed) | free tier |
| ~20 annotation calls | ~$0.05 |
| 1 daily overview call | ~$0.005 |
| Email send | free |
| **Total** | **~$0.05-0.10** |

About **$1.50-3.00/month** at one run per day. The `--max-content-chars`
cap is the biggest cost lever — set to 6000 by default; raise it if you
need more model context (linearly more expensive), lower for less.

---

## Architecture

```
content_search_seeds.txt   →  Tavily search
preferred_domains.txt      →  include_domains filter
                                   ↓
                          ~50-100 candidate URLs
                                   ↓
        URL dedup → Title dedup → MinHash dedup       (no API calls)
                                   ↓
            ~20 survivors  →  Claude Haiku 4.5         (structured outputs,
            (annotation:                                prompt-cached system
             summary +                                  prompt, paced 4s
             takeaways +                                between calls,
             category +                                 8 SDK retries)
             score +
             tags)
                                   ↓
            Rank by relevance, cap per-domain
                                   ↓
                   Top 10 selected
                                   ↓
                Claude → day overview (≤40 words)
                                   ↓
            data/daily/YYYY-MM-DD.json (persisted)
            data/articles.json (history for dedup)
            output/newsletter-YYYY-MM-DD.html (rendered)
            output/index.html (timeline UI)
                                   ↓
            Gmail SMTP → your inbox
            scripts/build_dist.py → dist/ → Vercel
```

---

## Author

Built by [Marcilio Mendonca, PhD](https://www.linkedin.com/in/marcilio/) —
Staff AI Forward Deployed Engineer at Google.

If you fork this, the branding (`NEWSLETTER_NAME` / `NEWSLETTER_AUTHOR_*`
env vars) is what to change. Otherwise — make it your own.

---

## License

MIT.
