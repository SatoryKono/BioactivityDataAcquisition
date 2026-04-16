#!/usr/bin/env bash
# Codex for headless machine (no MCP servers)
# Run from WSL: bash ./scripts/ops/codex-headless.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load API key
if [[ -f "${REPO_ROOT}/.env.codex" ]]; then
    set -a
    source "${REPO_ROOT}/.env.codex"
    set +a
fi

# Verify API key
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set"
    exit 1
fi

echo "[INFO] Starting Codex (headless mode - no MCP servers)..."
echo ""

# Get Codex binary
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Start Codex without MCP servers
exec "${CODEX_BIN}" -C "${REPO_ROOT}"
