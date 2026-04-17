#!/usr/bin/env bash
# Compatibility facade for the canonical Codex auto-execution launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"

if [[ ! -f "${ENSURE_SCRIPT}" ]]; then
    echo "[codex-exec] ERROR: bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
    exit 1
fi

CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

if [[ ! -x "${CODEX_BIN}" ]]; then
    "${ENSURE_SCRIPT}" --ensure >/dev/null
    CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
fi

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

exec "${CODEX_BIN}" exec --full-auto -C "${REPO_ROOT}" "$@"
