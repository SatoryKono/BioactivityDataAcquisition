#!/usr/bin/env bash
# Launch Codex CLI from WSL
# Codex will use the current working directory context
# Usage: ./codex.sh [options] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure_codex_cli.sh"

UPDATE_FLAG=""
if [[ "${1:-}" == "--update" ]]; then
    UPDATE_FLAG="--update"
    shift
fi

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    echo "[ERROR] Codex bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

CODEX_BIN="$("${ENSURE_SCRIPT}" ${UPDATE_FLAG:+$UPDATE_FLAG} --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Launch Codex
if [[ $# -eq 0 ]]; then
    echo "[codex] Starting interactive mode..."
    exec "${CODEX_BIN}" -C "${REPO_ROOT}"
else
    echo "[codex] Prompt: $*"
    exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
fi
