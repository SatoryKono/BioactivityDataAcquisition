#!/usr/bin/env bash
# Canonical Gemini launcher that skips MCP synchronization.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<'EOF'
Usage: ./headless.sh [command] [prompt]

Delegates to the canonical WSL launcher at scripts/ai/gemini/run-gemini.sh and
skips automatic MCP synchronization before launching Gemini.
EOF
    exit 0
fi

export GEMINI_SKIP_MCP_SETUP=1
exec bash "${SCRIPT_DIR}/run-gemini.sh" "$@"
