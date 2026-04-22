#!/usr/bin/env bash
# Helper: Launch Codex
# Called by: run-codex.sh/run-codex.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../../..")}"
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

# Use timeout on ENSURE_SCRIPT calls
CODEX_BIN="" 
CODEX_PREFIX=""
if timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin >/dev/null 2>&1; then
    CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || echo "")"
    CODEX_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-prefix 2>/dev/null || echo "")"
fi

if [[ -z "$CODEX_BIN" ]]; then
    echo "[INFO] Codex binary not found, attempting installation..."
    if timeout 120 "${ENSURE_SCRIPT}" --ensure >/dev/null 2>&1; then
        CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --print-bin 2>/dev/null || echo "")"
        CODEX_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --print-prefix 2>/dev/null || echo "")"
    fi
fi

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
    # Add 60-second timeout to prevent hanging on setup_mcp.py
    if ! timeout 60 "${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${CODEX_BIN}" >/dev/null 2>&1; then
        echo "[WARN] MCP setup timed out or failed, continuing anyway" >&2
    else
        echo "[INFO] MCP configuration synchronized"
    fi
fi

# Launch Codex
exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
