#!/usr/bin/env bash
# Canonical headless Codex launcher without MCP servers.

set -euo pipefail

print_help() {
    cat <<'EOF'
Codex Headless Launcher

Usage: headless.sh [args...]

Runs Codex without MCP setup. Requires OPENAI_API_KEY to be available
directly or through .env.codex in the repository root.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    print_help
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"

if [[ -f "${REPO_ROOT}/.env.codex" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env.codex"
    set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set"
    exit 1
fi

if [[ ! -f "${ENSURE_SCRIPT}" ]]; then
    echo "[ERROR] Codex bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

echo "[INFO] Starting Codex (headless mode - no MCP servers)..."
echo ""

CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
