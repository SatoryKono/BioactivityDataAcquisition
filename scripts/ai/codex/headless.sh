#!/usr/bin/env bash
# Canonical Codex launcher that skips MCP synchronization.

set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<'EOF'
Usage: ./headless.sh [command] [prompt]

Launch Codex with the same command surface as ./run-codex.sh, but skip the
automatic MCP synchronization step before starting Codex.

Examples:
  ./headless.sh
  ./headless.sh "analyze the code"
  ./headless.sh exec "refactor the parser"
  ./headless.sh check
EOF
    exit 0
fi

export CODEX_SKIP_MCP_SETUP=1
exec bash "${SCRIPT_DIR}/run-codex.sh" "$@"
