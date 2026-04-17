#!/usr/bin/env bash
# Codex Device Auth Login for Headless Machine
# Run from WSL: bash ./scripts/ops/codex-device-login.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo ""
echo "==========================================="
echo "  Codex Device Auth Login"
echo "==========================================="
echo ""

# Get Codex binary
ENSURE_SCRIPT="${SCRIPT_DIR}/support/ensure_codex_cli.sh"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

echo "[INFO] Starting device auth login..."
echo "[INFO] Follow the instructions below:"
echo ""

# Run device auth
"${CODEX_BIN}" login --device-auth

echo ""
echo "==========================================="
echo "  Login Complete!"
echo "==========================================="
echo ""
echo "You can now use Codex:"
echo "  codex"
echo "  codex \"your prompt\""
echo ""
