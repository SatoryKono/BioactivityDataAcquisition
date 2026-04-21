#!/usr/bin/env bash
# Helper: Setup Gemini CLI managed runtime.
# Called by: run-gemini.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-gemini-cli.sh"

if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
SEPARATOR="=================================================="

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
echo "${SEPARATOR}"
echo "  Gemini CLI Setup - Installation"
echo "${SEPARATOR}"
echo ""

log_info "STEP 1: Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    log_success "Node.js found: $(node --version)"
else
    log_error "Node.js not found"
    log_info "Install Node.js in WSL, then rerun: bash scripts/ai/gemini/run-gemini.sh setup"
    exit 1
fi

log_info "STEP 2: Checking npm..."
if command -v npm >/dev/null 2>&1; then
    log_success "npm found: $(npm --version)"
else
    log_error "npm not found"
    log_info "Install npm in WSL, then rerun: bash scripts/ai/gemini/run-gemini.sh setup"
    exit 1
fi

log_info "STEP 3: Installing Gemini CLI..."
if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    log_error "Bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

if ! "${ENSURE_SCRIPT}" --ensure >/dev/null; then
    log_error "Gemini CLI installation failed"
    exit 1
fi

GEMINI_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
GEMINI_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
log_success "Gemini CLI ready: $("${GEMINI_BIN}" --version 2>/dev/null || echo unknown)"
log_success "Binary: ${GEMINI_BIN}"
log_success "Prefix: ${GEMINI_PREFIX}"

log_info "STEP 4: Configuring .env.gemini..."
ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ ! -f "${ENV_FILE}" ]]; then
    cat > "${ENV_FILE}" <<EOF
# Google Gemini CLI Configuration
# Get your API key from: https://aistudio.google.com/app/apikeys
GEMINI_API_KEY=your-api-key-here
# Optional model override, if supported by the installed Gemini CLI.
# GEMINI_MODEL=gemini-2.5-flash
EOF
    log_warn ".env.gemini created - please edit and add your API key"
else
    log_success ".env.gemini exists"
fi

echo ""
echo "${SEPARATOR}"
log_success "Setup completed successfully!"
echo "${SEPARATOR}"
echo ""
log_info "Next steps:"
echo "  1. Edit scripts/ai/gemini/.env.gemini and add your Gemini API key"
echo "  2. Run: bash scripts/ai/gemini/run-gemini.sh"
echo ""
