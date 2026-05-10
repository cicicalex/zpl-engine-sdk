#!/bin/bash
# daily-status.sh — One-page snapshot of the ZPL ecosystem.
#
# Run ad-hoc, from cron, or from n8n. Emits:
#   - engine /health (version + status)
#   - public package versions (npm + PyPI)
#   - site /api/health for ZPL Main + Finance
#   - GitHub Pages OpenAPI accessible?
# and POSTs the rendered Markdown to Telegram if TELEGRAM_BOT_TOKEN +
# TELEGRAM_CHAT_ID are set in env. Otherwise prints to stdout.
#
# Exit code: 0 if everything green, 1 if anything is unreachable / stale.
# Designed so a CI runner can fail loud when the ecosystem starts to drift.

set -euo pipefail

# Defaults — override via env if you need to point at staging or fork.
ENGINE_URL="${ENGINE_URL:-https://engine.zeropointlogic.io}"
ZPL_MAIN_URL="${ZPL_MAIN_URL:-https://zeropointlogic.io}"
FINANCE_URL="${FINANCE_URL:-https://finance.zeropointlogic.io}"
PAGES_URL="${PAGES_URL:-https://cicicalex.github.io/zpl-engine-sdk/openapi.yaml}"

# ANSI colors (disabled if NO_COLOR or piping to non-tty)
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'; CYAN=$'\e[36m'; NC=$'\e[0m'
else
  GREEN=""; RED=""; YELLOW=""; CYAN=""; NC=""
fi

# Track overall health so we can return non-zero at the end.
overall_status=0

# Helpers --------------------------------------------------------------------

# `check_url <name> <url> <jq_path_or_-> <expected>` — fetch, parse, compare.
# `jq_path = -` means just check HTTP 200.
check_url() {
  local name="$1" url="$2" jq_path="$3" expected="${4:-}"
  local body http_code
  if ! body=$(curl -sS --max-time 10 -w '\n%{http_code}' "$url" 2>/dev/null); then
    echo "${RED}❌ ${name}${NC} unreachable"
    overall_status=1
    return
  fi
  http_code=$(echo "$body" | tail -1)
  body=$(echo "$body" | sed '$d')

  if [ "$http_code" != "200" ]; then
    echo "${RED}❌ ${name}${NC} HTTP $http_code"
    overall_status=1
    return
  fi

  if [ "$jq_path" = "-" ]; then
    echo "${GREEN}✅ ${name}${NC} HTTP 200"
    return
  fi

  local val
  val=$(echo "$body" | jq -r "$jq_path" 2>/dev/null || echo "")
  if [ -n "$expected" ] && [ "$val" != "$expected" ]; then
    echo "${YELLOW}⚠️  ${name}${NC} ${val} (expected ${expected})"
    overall_status=1
  else
    echo "${GREEN}✅ ${name}${NC} ${val}"
  fi
}

# `pkg_version <registry> <name>` — print the latest published version.
npm_version() {
  curl -sS --max-time 10 "https://registry.npmjs.org/$1/latest" 2>/dev/null \
    | jq -r '.version // "unreachable"' \
    || echo "unreachable"
}

pypi_version() {
  curl -sS --max-time 10 "https://pypi.org/pypi/$1/json" 2>/dev/null \
    | jq -r '.info.version // "unreachable"' \
    || echo "unreachable"
}

# Build the report --------------------------------------------------------

now=$(date -u '+%Y-%m-%d %H:%M UTC')

report=$(cat <<REPORT
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${CYAN}ZPL Daily Status — ${now}${NC}
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

${CYAN}Engine${NC}
$(check_url "engine /health"        "$ENGINE_URL/health"           '.status'   "ok")
$(check_url "engine /version"       "$ENGINE_URL/version" '.version' || true)

${CYAN}Sites${NC}
$(check_url "ZPL Main /api/health"  "$ZPL_MAIN_URL/api/health"     -)
$(check_url "Finance /api/health"   "$FINANCE_URL/api/health"      -)

${CYAN}Public docs${NC}
$(check_url "OpenAPI spec (Pages)"  "$PAGES_URL"                   -)

${CYAN}Published packages (latest on registry)${NC}
  npm  zpl-engine-mcp           : $(npm_version zpl-engine-mcp)
  npm  zpl-engine-cli           : $(npm_version zpl-engine-cli)
  npm  @zeropointlogic/sdk      : $(npm_version @zeropointlogic/sdk)
  pypi zeropointlogic           : $(pypi_version zeropointlogic)

REPORT
)

# Print the human-readable report (always)
echo "$report"

# Telegram delivery (optional) -------------------------------------------

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  # Strip ANSI codes for Telegram (it doesn't render them)
  plain=$(echo "$report" | sed -r 's/\x1b\[[0-9;]*m//g')

  # Telegram markdown limits: 4096 chars max. Our report is ~30 lines so safe.
  curl -sS --max-time 10 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "parse_mode=Markdown" \
    --data-urlencode "text=\`\`\`
${plain}
\`\`\`" \
    > /dev/null \
    && echo "${GREEN}✅${NC} Posted to Telegram" \
    || echo "${RED}❌${NC} Telegram POST failed"
fi

exit $overall_status
