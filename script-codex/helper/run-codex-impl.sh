#!/usr/bin/env bash
# Helper: Launch Codex
# Called by: run-codex.sh/run-codex.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2}"

# Load environment
ENV_FILE="${ROOT_DIR}/.env.codex"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# Verify API key
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set in ${ENV_FILE}"
    echo "[INFO] Please edit .env.codex and add your API key from: https://platform.openai.com/api-keys"
    exit 1
fi

# Find Codex binary - try multiple locations
CODEX_BIN=""

# Try 1: In PATH (most common - installed via npm -g)
if command -v codex >/dev/null 2>&1; then
    CODEX_BIN="codex"
    echo "[INFO] Using Codex from PATH: $(which codex)"
fi

# Try 2: Custom npm prefix location
if [[ -z "$CODEX_BIN" ]] && [[ -x "${HOME}/.cache/tools/codex-cli/npm-global/bin/codex" ]]; then
    CODEX_BIN="${HOME}/.cache/tools/codex-cli/npm-global/bin/codex"
    echo "[INFO] Using Codex from custom location: ${CODEX_BIN}"
fi

# Try 3: Default npm location
if [[ -z "$CODEX_BIN" ]] && [[ -x "${HOME}/.npm/bin/codex" ]]; then
    CODEX_BIN="${HOME}/.npm/bin/codex"
    echo "[INFO] Using Codex from npm bin: ${CODEX_BIN}"
fi

# If not found anywhere, try to install
if [[ -z "$CODEX_BIN" ]]; then
    echo "[INFO] Codex not found, attempting to install..."
    if timeout 180 npm install -g @openai/codex@latest 2>&1 | tail -10; then
        if command -v codex >/dev/null 2>&1; then
            CODEX_BIN="codex"
            echo "[INFO] Codex installed successfully"
        else
            echo "[ERROR] npm install succeeded but codex not found in PATH"
            exit 1
        fi
    else
        echo "[ERROR] Failed to install Codex"
        exit 1
    fi
fi

# Verify we found it
if [[ -z "$CODEX_BIN" ]] || ! command -v $CODEX_BIN >/dev/null 2>&1; then
    echo "[ERROR] Codex binary not found"
    echo "[INFO] Try installing manually: npm install -g @openai/codex"
    exit 1
fi

# Setup environment
export PATH="/usr/local/bin:${PATH}"

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Launch Codex
exec $CODEX_BIN -C "${REPO_ROOT}" "$@"
