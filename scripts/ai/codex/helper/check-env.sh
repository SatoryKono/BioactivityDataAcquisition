#!/usr/bin/env bash
# Helper: Check and setup Codex environment (WSL)
# Called by: run-codex.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"

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
if grep -qi microsoft /proc/version 2>/dev/null; then
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

# 4. Check API Key
log_info "Checking API key..."
ENV_FILE="${ROOT_DIR}/.env.codex"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -Eq 'OPENAI_API_KEY="?sk-' "${ENV_FILE}"; then
        log_success "API key found in .env.codex"
    else
        log_warn ".env.codex exists but API key missing or invalid"
        ALL_CHECKS=false
    fi
else
    log_warn ".env.codex not found"
    ALL_CHECKS=false
fi

# 5. Check Codex binary
log_info "Checking Codex CLI..."
CODEX_BIN=""
if [[ -x "${ENSURE_SCRIPT}" ]]; then
    CODEX_BIN="$("${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || true)"
fi
if [[ -x "${CODEX_BIN}" ]]; then
    CODEX_VER=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")
    log_success "Codex CLI is installed: $CODEX_VER"
else
    log_warn "Codex CLI not found"
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
