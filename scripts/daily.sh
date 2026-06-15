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

# Hold the Mac awake for the full run, then let it idle-sleep again.
# The scheduled wake (pmset) is aligned to this job's minute so the Mac can't
# idle-sleep (pmset sleep=1) in the gap before we start; once we're running,
# re-exec under caffeinate to stay awake for the whole cycle:
#   -i block idle sleep, -s block system sleep — released when this exits.
if [ -z "${_CAFFEINATED:-}" ]; then
    exec env _CAFFEINATED=1 caffeinate -i -s "$0" "$@"
fi

PROJECT_DIR="/Users/marcilio/projects/researcher-agent-dashboard"
cd "$PROJECT_DIR"

# Pull the recipient from .env (gitignored) so it stays out of this tracked
# script. We extract just this one key rather than sourcing .env, because
# bash `source` would try to execute values containing spaces (e.g. the
# Gmail app password) as commands.
NEWSLETTER_EMAIL_TO="$(grep -E '^NEWSLETTER_EMAIL_TO=' .env 2>/dev/null | tail -1 | cut -d= -f2-)"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

log "=== daily cycle start ==="

# --- host status snapshot: helps debug failed unattended runs after the fact.
# All best-effort (|| true) so a probe failure never aborts the cycle.
log "host status (for debugging unattended runs):"
log "  uptime  : $(uptime 2>/dev/null || true)"
while IFS= read -r _l; do [ -n "$_l" ] && log "  power   : ${_l}"; done < <(pmset -g batt 2>/dev/null || true)
_wake="$( (pmset -g log 2>/dev/null | grep -E 'Wake from|DarkWake from' | tail -1 | tr -s ' ') || true)"
log "  lastwake: ${_wake:-unknown}"

# After a scheduled wake, Wi-Fi may not be reconnected yet. Wait up to ~60s for
# the search host to be reachable before starting, so the run doesn't die on a
# cold-network timeout. (The search step also retries internally as a backstop.)
log "  waiting for network (api.tavily.com reachable)..."
_net="UNREACHABLE after ~60s"
for _i in $(seq 1 30); do
    if curl -s --max-time 3 -o /dev/null https://api.tavily.com; then
        _net="reachable on attempt ${_i} (~$(( (_i - 1) * 2 ))s after wake)"
        break
    fi
    sleep 2
done
log "  network : ${_net}"

log "step 1/3: agent run"
.venv/bin/researcher-dashboard \
    --search-file content_search_seeds.txt \
    --search-provider tavily \
    --domain-mode strict \
    --email-to "${NEWSLETTER_EMAIL_TO:?set NEWSLETTER_EMAIL_TO in .env}"

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
