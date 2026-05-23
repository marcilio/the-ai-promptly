#!/usr/bin/env bash
# Daily Agentic — full daily cycle, intended to be invoked by launchd.
#
# Steps:
#   1. Run the agent (search → dedup → annotate → render → email)
#   2. Build the static deploy bundle
#   3. Commit + push if there are changes → Vercel auto-redeploys
#
# Logs go to ~/Library/Logs/daily-agentic.{out,err}.log via the plist's
# StandardOutPath / StandardErrorPath; this script just emits timestamped
# lines that show up there.

set -euo pipefail

PROJECT_DIR="/Users/marcilio/projects/researcher-agent-dashboard"
cd "$PROJECT_DIR"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

log "=== daily cycle start ==="

log "step 1/3: agent run"
.venv/bin/researcher-dashboard \
    --search-file content_search_seeds.txt \
    --search-provider tavily \
    --domain-mode strict \
    --email-to marcilio.mendonca@gmail.com

log "step 2/3: build dist"
.venv/bin/python scripts/build_dist.py

log "step 3/3: publish"
git add dist
if git diff --cached --quiet; then
    log "no dist changes — nothing to publish (Vercel deploy skipped)"
else
    git commit -m "Update $(date +%F)"
    git push
    log "pushed → Vercel will redeploy in ~30s"
fi

log "=== daily cycle done ==="
