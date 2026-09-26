#!/usr/bin/env bash
# INTERNAL: Helper: Check and setup Codex environment (WSL)
# Called by: run-codex.sh
# DO NOT invoke directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../..")}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${SCRIPT_DIR}/ensure-mcp.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[⚠]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}[✗]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

echo ""
echo "=================================================="
echo "  Codex Environment Check (WSL)"
echo "=================================================="
echo ""

ALL_CHECKS=true

# 1. Check if in WSL
log_info "Checking WSL environment..."
if [[ -f /proc/version ]] && timeout 2 grep -q microsoft /proc/version 2>/dev/null; then
    log_success "Running in WSL"
else
    log_error "Not running in WSL - this script requires WSL"
    exit 1
fi

# 2. Check Node.js
log_info "Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version)
    log_success "Node.js is installed: $NODE_VER"
else
    log_warn "Node.js not found"
    ALL_CHECKS=false
fi

# 3. Check npm
log_info "Checking npm..."
if command -v npm >/dev/null 2>&1; then
    NPM_VER=$(npm --version)
    log_success "npm is installed: $NPM_VER"
else
    log_warn "npm not found"
    ALL_CHECKS=false
fi

# 4. Check auth (API key in .env.codex OR persisted ChatGPT tokens in ~/.codex/auth.json)
# shellcheck source=codex-auth-lib.sh
source "${SCRIPT_DIR}/codex-auth-lib.sh"
log_info "Checking Codex authentication..."
ENV_FILE="${ROOT_DIR}/.env.codex"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi
AUTH_KIND="$(codex_auth_status_label || true)"
case "${AUTH_KIND}" in
    api-key)
        log_success "API key available (env/.env.codex)"
        ;;
    chatgpt-auth)
        log_success "ChatGPT auth found in $(codex_auth_file)"
        ;;
    *)
        if [[ -f "${ENV_FILE}" ]]; then
            log_warn ".env.codex exists but API key missing/invalid, and no ChatGPT auth in ~/.codex/auth.json"
        else
            log_warn "No .env.codex API key and no ChatGPT auth in ~/.codex/auth.json"
        fi
        log_info "Fix: bash scripts/ai/codex/run-codex.sh device-login  OR  set OPENAI_API_KEY in scripts/ai/codex/.env.codex"
        ALL_CHECKS=false
        ;;
esac

# 5. Check Codex binary
log_info "Checking Codex CLI..."
CODEX_BIN=""
if [[ -f "${ENSURE_SCRIPT}" ]]; then
    CODEX_BIN="$(timeout 10 bash "${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || true)"
fi
if [[ -x "${CODEX_BIN}" ]]; then
    CODEX_VER=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")
    log_success "Codex CLI is installed: $CODEX_VER"
else
    log_warn "Codex CLI not found"
    ALL_CHECKS=false
fi

# 6. Check MCP configuration
log_info "Checking MCP configuration..."
if [[ -f "${ENSURE_MCP_SCRIPT}" ]]; then
    if timeout 30 bash "${ENSURE_MCP_SCRIPT}" --check --codex-bin "${CODEX_BIN}" >/dev/null 2>&1; then
        log_success "MCP configuration is ready"
    else
        log_warn "MCP configuration is missing or stale"
        ALL_CHECKS=false
    fi
else
    log_warn "MCP setup helper not found"
    ALL_CHECKS=false
fi

echo ""

# Return exit code
if [[ "${ALL_CHECKS}" == "true" ]]; then
    log_success "All checks passed"
    exit 0
else
    log_warn "Some checks failed - will attempt to fix"
    exit 1
fi
