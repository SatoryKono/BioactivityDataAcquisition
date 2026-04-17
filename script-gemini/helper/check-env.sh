#!/usr/bin/env bash
# Helper: Check Gemini environment (WSL)
# Called by: run-gemini.sh

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
    local message="${1}"
    echo -e "${GREEN}[OK]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1}"
    echo -e "${YELLOW}[!]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1}"
    echo -e "${RED}[X]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1}"
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

# 2. Check Python3
log_info "Checking Python3..."
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version)
    log_success "Python3 is installed: $PY_VER"
else
    log_warn "Python3 not found"
    ALL_CHECKS=false
fi

# 3. Check pip3
log_info "Checking pip3..."
if command -v pip3 >/dev/null 2>&1; then
    PIP_VER=$(pip3 --version)
    log_success "pip3 is installed: $PIP_VER"
else
    log_warn "pip3 not found"
    ALL_CHECKS=false
fi

# 4. Check google-generativeai package
log_info "Checking Gemini Python SDK..."
PYTHON_BIN="python3"
VENV_DIR="${HOME}/.cache/tools/gemini-venv"
if [[ -x "${VENV_DIR}/bin/python" ]]; then
    PYTHON_BIN="${VENV_DIR}/bin/python"
fi

if "${PYTHON_BIN}" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('google.genai') or importlib.util.find_spec('google.generativeai') else 1)" 2>/dev/null; then
    if "${PYTHON_BIN}" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('google.genai') else 1)" 2>/dev/null; then
        log_success "Google GenAI SDK is installed"
    else
        log_warn "Legacy google-generativeai package is installed; rerun setup to migrate"
    fi
else
    log_warn "Gemini Python SDK not installed"
    ALL_CHECKS=false
fi

# 5. Check API Key
log_info "Checking API key..."
ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ -f "${ENV_FILE}" ]]; then
    if grep -q "GEMINI_API_KEY=AIzaSy" "${ENV_FILE}"; then
        log_success "API key found in .env.gemini"
    elif grep -q "GEMINI_API_KEY=" "${ENV_FILE}" && ! grep -q "GEMINI_API_KEY=your-api-key-here" "${ENV_FILE}"; then
        log_success "API key found in .env.gemini"
    else
        log_warn ".env.gemini exists but API key missing or not set"
        ALL_CHECKS=false
    fi
else
    log_warn ".env.gemini not found"
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
