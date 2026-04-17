#!/bin/bash

# sync-agents-codex-to-gemini.sh
# Syncs py-* agent profiles from Codex to Gemini workspace
# Allows Gemini to use same agent definitions as Codex

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CODEX_AGENTS="${PROJECT_ROOT}/.codex/agents"
GEMINI_AGENTS="${PROJECT_ROOT}/.gemini/agents"

if [ ! -d "${CODEX_AGENTS}" ]; then
  echo "❌ Codex agents directory not found: ${CODEX_AGENTS}"
  exit 1
fi

mkdir -p "${GEMINI_AGENTS}"

# Sync specific BioETL profiles
PROFILES=(
  "py-audit-bot.md"
  "py-architecture-debt-bot.md"
  "py-config-bot.md"
  "py-debug-bot.md"
  "py-doc-bot.md"
  "py-plan-bot.md"
  "py-test-bot.md"
  "py-test-swarm.md"
  "py-review-orchestrator.md"
)

echo "🔄 Syncing agent profiles from Codex to Gemini..."
echo ""

COUNT=0
for profile in "${PROFILES[@]}"; do
  SRC="${CODEX_AGENTS}/${profile}"
  DST="${GEMINI_AGENTS}/${profile}"
  
  if [ -f "${SRC}" ]; then
    cp "${SRC}" "${DST}"
    echo "✓ ${profile}"
    ((COUNT++))
  else
    echo "⊘ ${profile} (not found in Codex)"
  fi
done

echo ""
echo "✅ Synced ${COUNT} agent profiles to Gemini"
echo ""
echo "Available profiles in .gemini/agents/:"
ls -1 "${GEMINI_AGENTS}"/*.md 2>/dev/null | xargs -n1 basename || true
