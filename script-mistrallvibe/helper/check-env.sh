#!/usr/bin/env bash
# Helper: Check Mistral Vibe environment
# Called by: run-mistrallvibe.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Mistral Vibe Environment Check"
echo "=================================================="
echo ""

ALL_CHECKS=true

# 1. Check Node.js
log_info "Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version)
    log_success "Node.js installed: $NODE_VER"
else
    log_warn "Node.js not found"
    ALL_CHECKS=false
fi

# 2. Check npm
log_info "Checking npm..."
if command -v npm >/dev/null 2>&1; then
    NPM_VER=$(npm --version)
    log_success "npm installed: $NPM_VER"
else
    log_warn "npm not found"
    ALL_CHECKS=false
fi

# 3. Check .env.mistrallvibe
log_info "Checking configuration..."
ENV_FILE="${ROOT_DIR}/.env.mistrallvibe"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -q "VIBE_API_KEY=" "${ENV_FILE}"; then
        if grep -q "your-api-key-here" "${ENV_FILE}"; then
            log_warn ".env.mistrallvibe exists but VIBE_API_KEY not configured"
            ALL_CHECKS=false
        else
            log_success ".env.mistrallvibe configured with API key"
        fi
    else
        log_warn ".env.mistrallvibe exists but missing VIBE_API_KEY"
        ALL_CHECKS=false
    fi
else
    log_warn ".env.mistrallvibe not found"
    ALL_CHECKS=false
fi

# 4. Check if Vibe is installed
log_info "Checking Mistral Vibe installation..."
if command -v vibe >/dev/null 2>&1; then
    VIBE_VER=$(vibe --version 2>/dev/null || echo "unknown")
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
