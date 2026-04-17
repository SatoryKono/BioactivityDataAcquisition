#!/bin/bash

# lib/sync.sh - Sync agent profiles from Codex to Gemini

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use PROJECT_ROOT from environment, or calculate it
if [ -z "$PROJECT_ROOT" ]; then
  # From lib/ go up 3 levels to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
fi

# Set paths based on PROJECT_ROOT
CODEX_AGENTS="${PROJECT_ROOT}/.codex/agents"
GEMINI_AGENTS="${PROJECT_ROOT}/.gemini/agents"

# Export for sourced utils
export PROJECT_ROOT

source "${SCRIPT_DIR}/utils.sh"

print_header
print_section "Syncing agent profiles from Codex to Gemini"

if [ ! -d "${CODEX_AGENTS}" ]; then
  print_error "Codex agents directory not found: ${CODEX_AGENTS}"
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

echo ""
count=0
for profile in "${PROFILES[@]}"; do
  SRC="${CODEX_AGENTS}/${profile}"
  DST="${GEMINI_AGENTS}/${profile}"
  
  if [ -f "${SRC}" ]; then
    cp "${SRC}" "${DST}" 2>/dev/null || true
    print_success "$profile"
    ((count++))
  else
    print_warning "$profile (not found in Codex)"
  fi
done

echo ""
print_success "Synced ${count} agent profiles to Gemini"
echo ""
