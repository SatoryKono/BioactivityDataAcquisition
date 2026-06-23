#!/usr/bin/env bash
# Thin compatibility wrapper for the canonical Gemini launcher.
# Usage: bash gemini-interactive.sh [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<'EOF'
Usage: ./gemini-interactive.sh [prompt]

Thin compatibility wrapper that delegates to scripts/ai/gemini/run-gemini.sh.
With no arguments it starts interactive mode; with arguments it treats them as a
single prompt request.
EOF
    exit 0
fi

if [[ $# -gt 0 ]]; then
    exec bash "${SCRIPT_DIR}/run-gemini.sh" "$@"
else
    exec bash "${SCRIPT_DIR}/run-gemini.sh" start
fi
