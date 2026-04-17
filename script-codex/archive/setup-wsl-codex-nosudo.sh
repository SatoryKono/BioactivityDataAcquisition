#!/usr/bin/env bash
# WSL Codex Setup — No Sudo Required
# Run from WSL: bash ./scripts/ops/setup-wsl-codex-nosudo.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_error() {
    local message="${1:-}"
    echo -e "${RED}[ERROR]${NC} ${message}" >&2
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[WARN]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[INFO]${NC} ${message}" >&2
    return 0
}

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENSURE_SCRIPT="${SCRIPT_DIR}/support/ensure_codex_cli.sh"
SEPARATOR="==========================================="

echo ""
echo "${SEPARATOR}"
echo "  WSL Codex Setup (No Sudo)"
echo "${SEPARATOR}"
echo ""

log_info "This setup does NOT require sudo password"
echo ""

# Step 1: Check Node.js
log_info "Step 1: Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version)
    log_success "Node.js $NODE_VER found"
else
    log_warn "Node.js not found"
    log_info "To install: sudo apt-get install -y nodejs npm"
    log_info "Or install from: https://nodejs.org/"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Step 2: Check npm
log_info "Step 2: Checking npm..."
if command -v npm >/dev/null 2>&1; then
    NPM_VER=$(npm --version)
    log_success "npm $NPM_VER found"
else
    log_error "npm not found. Node.js may not be installed."
    log_info "To install: sudo apt-get install -y nodejs npm"
    exit 1
fi
echo ""

# Step 3: Install Codex
log_info "Step 3: Installing Codex CLI..."
echo ""

CACHE_DIR="${REPO_ROOT}/.cache/tools"
mkdir -p "${CACHE_DIR}"

if "${ENSURE_SCRIPT}" --update 2>&1 | grep -E '(Installing|Updating|ERROR)'; then
    log_success "Codex CLI installation completed"
fi

CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"

if [[ ! -x "${CODEX_BIN}" ]]; then
    log_error "Codex binary not executable: ${CODEX_BIN}"
    exit 1
fi

CODEX_VERSION=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")
log_success "Codex $CODEX_VERSION installed"
echo ""

# Step 4: Test Codex
log_info "Step 4: Testing Codex..."
if "${CODEX_BIN}" --help &>/dev/null; then
    log_success "Codex CLI responds to --help"
else
    log_warn "Codex --help check had issues (may still be functional)"
fi
echo ""

# Step 5: Load proxy if available
log_info "Step 5: Proxy configuration..."
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
    if [[ -n "${http_proxy:-}" ]]; then
        log_success "Proxy configured: $http_proxy"
    else
        log_warn "Proxy config file exists but proxy not set"
    fi
else
    log_warn "Proxy config not found (optional)"
fi
echo ""

echo "${SEPARATOR}"
echo "  Setup Complete!"
echo "${SEPARATOR}"
echo ""
echo "What's installed:"
echo "  • Node.js: $(node --version)"
echo "  • npm: $(npm --version)"
echo "  • Codex: $CODEX_VERSION"
echo ""
echo "Next steps:"
echo ""
echo "1. From PowerShell, test Codex:"
echo "   .\scripts\ops\codex.bat \"analyze the pipeline\""
echo ""
echo "2. Or interactive mode:"
echo "   .\scripts\ops\codex.bat"
echo ""
echo "3. For auto-execution:"
echo "   .\scripts\ops\codex-exec.bat \"your prompt\""
echo ""
echo "Documentation:"
echo "   cat $REPO_ROOT/scripts/ops/POWERSHELL_QUICK_START.md"
echo ""
