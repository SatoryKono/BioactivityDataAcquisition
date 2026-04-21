#!/usr/bin/env bash
# Helper: Check Gemini environment (WSL)
# Called by: run-gemini.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-gemini-cli.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[OK]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[!]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}[X]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

echo ""
echo "=================================================="
echo "  Gemini Environment Check (WSL)"
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

# 4. Check managed Gemini CLI
log_info "Checking Gemini CLI..."
GEMINI_BIN=""
if [[ -x "${ENSURE_SCRIPT}" ]]; then
    GEMINI_BIN="$("${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || true)"
    GEMINI_PREFIX="$("${ENSURE_SCRIPT}" --no-install --print-prefix 2>/dev/null || true)"
fi

if [[ -x "${GEMINI_BIN}" ]]; then
    GEMINI_HOME="$(cd "${GEMINI_PREFIX}/.." && pwd)/home"
    GEMINI_VER=$(GEMINI_CLI_HOME="${GEMINI_HOME}" PATH="${GEMINI_PREFIX}/bin:${PATH}" "${GEMINI_BIN}" --version 2>/dev/null || echo "unknown")
    log_success "Gemini CLI is installed: $GEMINI_VER"
else
    log_warn "Gemini CLI not found"
    ALL_CHECKS=false
fi

# 5. Check API Key
log_info "Checking API key..."
ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -Eq '^GEMINI_API_KEY="?[^"#[:space:]]+' "${ENV_FILE}" && ! grep -q "GEMINI_API_KEY=your-api-key-here" "${ENV_FILE}"; then
        log_success "API key found in .env.gemini"
    else
        log_warn ".env.gemini exists but API key missing or not set"
        ALL_CHECKS=false
    fi
else
    log_warn ".env.gemini not found"
    ALL_CHECKS=false
fi

# 6. Create .env.gemini template if missing
if [[ ! -f "${ENV_FILE}" ]]; then
    log_warn "Creating .env.gemini template..."
    cat > "${ENV_FILE}" <<EOF
# Google Gemini Configuration
# Get your API key from: https://aistudio.google.com/app/apikeys
GEMINI_API_KEY=your-api-key-here
# Optional model override
# GEMINI_MODEL=gemini-2.5-flash
EOF
    log_warn ".env.gemini created - please edit and add your API key"
fi

echo ""

# Return exit code
if [[ "${ALL_CHECKS}" == "true" ]]; then
    log_success "All checks passed"
    exit 0
else
    log_warn "Some checks failed"
    exit 1
fi
