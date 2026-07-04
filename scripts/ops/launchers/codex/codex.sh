#!/usr/bin/env bash
# Compatibility facade for the canonical Codex launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/scripts/ai/codex/helper/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${REPO_ROOT}/scripts/ai/codex/helper/ensure-mcp.sh"

if [[ ! -f "${ENSURE_SCRIPT}" ]]; then
    echo "[codex] ERROR: bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
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

if [[ "${CODEX_SKIP_MCP_SETUP:-0}" != "1" ]]; then
    if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
        echo "[codex] ERROR: MCP setup helper not found: ${ENSURE_MCP_SCRIPT}" >&2
        exit 1
    fi
    if ! timeout 60 "${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${CODEX_BIN}" >/dev/null 2>&1; then
        echo "[codex] WARN: MCP setup timed out or failed, continuing anyway" >&2
    fi
fi

exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
