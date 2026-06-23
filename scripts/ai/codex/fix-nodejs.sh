#!/usr/bin/env bash
# Fix Node.js version in WSL - IMPROVED
# Run from: cd /path/to/repo/scripts/ai/codex && bash fix-nodejs.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[i]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }

echo ""
echo "=================================================="
echo "  Node.js Fix for Codex"
echo "=================================================="
echo ""

# Get current directory
CURRENT_DIR="$(pwd)"
log_info "Current directory: ${CURRENT_DIR}"

# Check if we're in the right place
if [[ ! -f "run-codex.sh" ]]; then
    log_error "run-codex.sh not found in current directory!"
    log_info "Please run from: cd /path/to/repo/scripts/ai/codex && bash fix-nodejs.sh"
    exit 1
fi

SCRIPT_DIR="${CURRENT_DIR}"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_success "Found codex directory: ${SCRIPT_DIR}"
log_success "Found helper directory: ${HELPER_DIR}"
log_success "Found repo root: ${REPO_ROOT}"
echo ""

# Check current version
log_info "Current Node.js version:"
node --version 2>/dev/null || log_warn "Node.js not found"
npm --version 2>/dev/null || log_warn "npm not found"
echo ""

# Step 1: Remove old Node.js if installed via apt
log_info "Removing old Node.js from system..."
sudo apt-get remove -y nodejs npm 2>/dev/null || true
sudo apt-get autoremove -y 2>/dev/null || true
echo ""

# Step 2: Download Node.js 20 LTS
log_info "Downloading Node.js 20 LTS..."
cd /tmp
if ! curl -fsSL https://nodejs.org/dist/v20.10.0/node-v20.10.0-linux-x64.tar.xz -o node-v20.10.0-linux-x64.tar.xz 2>/dev/null; then
    log_error "Failed to download Node.js"
    exit 1
fi
log_success "Downloaded"
echo ""

# Step 3: Extract and install
log_info "Installing Node.js..."
sudo tar -xJf node-v20.10.0-linux-x64.tar.xz -C /usr/local --strip-components=1
log_success "Installed"
echo ""

# Step 4: Verify and reload PATH
log_info "Verifying installation..."
export PATH="/usr/local/bin:$PATH"
hash -r
node_ver=$(node --version)
npm_ver=$(npm --version)
log_success "Node.js: $node_ver"
log_success "npm: $npm_ver"
echo ""

# Step 5: Reinstall Codex
log_info "Reinstalling Codex CLI..."
cd "${SCRIPT_DIR}"

if [[ ! -d "${HELPER_DIR}" ]]; then
    log_error "Helper directory not found: ${HELPER_DIR}"
    exit 1
fi

if [[ ! -x "${HELPER_DIR}/setup-env.sh" ]]; then
    log_error "setup-env.sh not found or not executable: ${HELPER_DIR}/setup-env.sh"
    exit 1
fi

log_info "Running setup from: ${HELPER_DIR}/setup-env.sh"
echo ""
bash "${HELPER_DIR}/setup-env.sh"

echo ""
echo "=================================================="
log_success "Node.js fixed!"
echo "=================================================="
echo ""
log_info "Verification:"
node --version
npm --version
echo ""
log_success "Next: Run Codex"
echo ""
echo "  cd ${SCRIPT_DIR}"
echo "  bash run-codex.sh"
echo ""
