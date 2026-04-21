#!/usr/bin/env bash
# Helper: Launch Codex
# Called by: run-codex.sh/run-codex.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${SCRIPT_DIR}/ensure-mcp.sh"

# Load environment
ENV_FILE="${ROOT_DIR}/.env.codex"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# Verify API key
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set in ${ENV_FILE}" >&2
    echo "[INFO] Please edit .env.codex and add your API key from: https://platform.openai.com/api-keys" >&2
    exit 1
fi

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    echo "[ERROR] Codex bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
    exit 1
fi

CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
echo "[INFO] Using Codex from managed prefix: ${CODEX_BIN}"

# Verify we found it
if [[ -z "$CODEX_BIN" ]] || [[ ! -x "${CODEX_BIN}" ]]; then
    echo "[ERROR] Codex binary not found" >&2
    echo "[INFO] Try running: bash ${ENSURE_SCRIPT} --ensure" >&2
    exit 1
fi

# Setup environment
export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:/usr/local/bin:${PATH}"

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Keep Codex's native config.toml in sync with the repo MCP config before
# launching. Codex reads ~/.codex/config.toml, not .mcp.json directly.
if [[ "${CODEX_SKIP_MCP_SETUP:-0}" != "1" ]]; then
    if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
        echo "[ERROR] MCP setup helper not found: ${ENSURE_MCP_SCRIPT}" >&2
        exit 1
    fi
    "${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${CODEX_BIN}" >/dev/null
    echo "[INFO] MCP configuration synchronized"
fi

# Launch Codex
exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
