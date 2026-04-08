#!/usr/bin/env bash
# Launch Codex in auto-execution mode (full-auto) from WSL
# Runs with auto-approval without confirmations
# Usage: ./codex-exec.sh "prompt"

set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: codex-exec.sh \"prompt\""
    echo ""
    echo "Runs Codex in full-auto mode without confirmations."
    echo "Example: codex-exec.sh \"refactor ChemBL parser for performance\""
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Verify Codex is installed
if ! command -v codex &>/dev/null; then
    echo "[codex-exec] ERROR: Codex not found"
    echo "[codex-exec] Install: npm install -g @openai/codex"
    exit 1
fi

# Launch in full-auto mode
echo "[codex-exec] Prompt: $*"
exec codex exec --full-auto -C "$REPO_ROOT" "$@"
