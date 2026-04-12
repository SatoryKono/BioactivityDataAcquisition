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
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure_codex_cli.sh"

UPDATE_FLAG=""
if [[ "${1:-}" == "--update" ]]; then
    UPDATE_FLAG="--update"
    shift
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: codex-exec.sh [--update] \"prompt\""
    exit 1
fi

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    echo "[codex-exec] ERROR: Codex bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

CODEX_BIN="$("${ENSURE_SCRIPT}" ${UPDATE_FLAG:+$UPDATE_FLAG} --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Launch in full-auto mode
echo "[codex-exec] Prompt: $*"
exec "${CODEX_BIN}" exec --full-auto -C "$REPO_ROOT" "$@"
