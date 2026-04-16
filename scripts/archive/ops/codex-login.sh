#!/usr/bin/env bash
# Load Codex environment and start interactive mode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load .env.codex if exists
if [[ -f "${REPO_ROOT}/.env.codex" ]]; then
    set -a  # Export all variables
    source "${REPO_ROOT}/.env.codex"
    set +a  # Stop exporting
fi

# Load OpenAI key from .env if exists (but not other variables that might break things)
if [[ -f "${REPO_ROOT}/.env" ]]; then
    # Only load OPENAI_API_KEY from .env, skip others
    if grep -q "OPENAI_API_KEY" "${REPO_ROOT}/.env"; then
        export OPENAI_API_KEY=$(grep "^OPENAI_API_KEY" "${REPO_ROOT}/.env" | cut -d= -f2-)
    fi
fi

# Verify API key is set
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set"
    echo "[INFO] Set it in .env.codex or with: export OPENAI_API_KEY='your-key'"
    exit 1
fi

echo "[INFO] OPENAI_API_KEY loaded"
echo "[INFO] Starting Codex..."
echo ""

# Get Codex binary
ENSURE_SCRIPT="${SCRIPT_DIR}/support/ensure_codex_cli.sh"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Start Codex
exec "${CODEX_BIN}" -C "${REPO_ROOT}"
