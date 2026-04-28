#!/usr/bin/env bash
# Helper: Check Mistral Vibe environment
# Called by: python -m scripts.ai vibe check

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
echo "  Mistral Vibe Environment Check"
echo "=================================================="
echo ""

ALL_CHECKS=true

# 1. Check Node.js
log_info "Checking Node.js..."
if timeout 10 bash -c "command -v node >/dev/null 2>&1"; then
    NODE_VER=$(timeout 5 node --version 2>/dev/null || echo "unknown")
    log_success "Node.js installed: $NODE_VER"
else
    log_warn "Node.js not found"
    ALL_CHECKS=false
fi

# 2. Check npm
log_info "Checking npm..."
if timeout 10 bash -c "command -v npm >/dev/null 2>&1"; then
    NPM_VER=$(timeout 5 npm --version 2>/dev/null || echo "unknown")
    log_success "npm installed: $NPM_VER"
else
    log_warn "npm not found"
    ALL_CHECKS=false
fi

# 3. Check .env.mistrallvibe
log_info "Checking configuration..."
ENV_FILE="${ROOT_DIR}/.env.mistrallvibe"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -qE "^(MISTRAL_API_KEY|VIBE_API_KEY)=" "${ENV_FILE}"; then
        if grep -q "your-api-key-here" "${ENV_FILE}"; then
            log_warn ".env.mistrallvibe exists but API key not configured"
            ALL_CHECKS=false
        else
            log_success ".env.mistrallvibe configured with API key"
        fi
    else
        log_warn ".env.mistrallvibe exists but missing MISTRAL_API_KEY"
        ALL_CHECKS=false
    fi
else
    log_warn ".env.mistrallvibe not found"
    ALL_CHECKS=false
fi

# 4. Check if Vibe is installed
log_info "Checking Mistral Vibe installation..."
if timeout 10 bash -c "command -v vibe >/dev/null 2>&1"; then
    VIBE_VER=$(timeout 5 vibe --version 2>/dev/null || echo "unknown")
    log_success "Mistral Vibe installed: $VIBE_VER"
else
    log_warn "Mistral Vibe not found in PATH"
    ALL_CHECKS=false
fi

echo ""

# Return exit code
if [[ "${ALL_CHECKS}" == "true" ]]; then
    log_success "All checks passed"
    exit 0
else
    log_warn "Some checks failed - run setup first"
    exit 1
fi
