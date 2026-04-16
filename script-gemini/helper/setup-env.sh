#!/usr/bin/env bash
# Helper: Setup Gemini environment
# Called by: run-gemini.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2}"

# Load proxy FIRST before any network operations
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Gemini Setup - Installing Missing Components"
echo "=================================================="
echo ""

# 1. Install Python3 if needed
if ! command -v python3 >/dev/null 2>&1; then
    log_info "Installing Python3..."
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y -qq python3 python3-pip python3-venv 2>/dev/null || sudo apt-get install -y python3 python3-pip python3-venv
    log_success "Python3 installed: $(python3 --version)"
fi

# 2. Create virtual environment
VENV_DIR="${HOME}/.cache/tools/gemini-venv"
mkdir -p "$(dirname "${VENV_DIR}")"

if [[ ! -d "${VENV_DIR}" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv "${VENV_DIR}"
    log_success "Virtual environment created"
fi

# 3. Install google-generativeai in venv
log_info "Installing Google GenAI SDK in venv..."
"${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
"${VENV_DIR}/bin/pip" install --upgrade google-genai

log_success "Google GenAI SDK installed in venv"

# 4. Create .env.gemini if needed
ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ ! -f "${ENV_FILE}" ]]; then
    log_info "Creating .env.gemini template..."
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
log_success "Setup complete!"
exit 0
