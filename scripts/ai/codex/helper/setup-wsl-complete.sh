#!/usr/bin/env bash
# Comprehensive WSL Codex Setup
# Run from WSL: bash ./scripts/ai/codex/helper/setup-wsl-complete.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_header() {
    local message="${1:-}"
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} ${message}"
    return 0
}

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}✓${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}⚠${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}✗${NC} ${message}" >&2
    return 0
}

# Detect environment
check_wsl() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_success "Running in WSL"
        return 0
    else
        log_error "Not running in WSL. This script requires WSL2."
        log_error "Run from WSL: wsl -- bash ./scripts/ai/codex/helper/setup-wsl-complete.sh"
        exit 1
    fi
    return 0
}

# Setup directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"
CACHE_DIR="${REPO_ROOT}/.cache/tools"
SEPARATOR="==========================================="

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    log_error "Codex bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

echo ""
echo "${SEPARATOR}"
echo "  WSL Codex Complete Setup"
echo "${SEPARATOR}"
echo ""

log_header "Step 0: Environment Check"
check_wsl

echo ""
log_header "Step 1: System Updates"

if ! command -v sudo &>/dev/null; then
    log_warn "sudo not found, skipping apt update"
else
    # Retry logic for apt-get update
    max_attempts=3
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if sudo apt-get update -qq 2>/dev/null; then
            log_success "Package manager updated"
            break
        else
            if [[ $attempt -lt $max_attempts ]]; then
                log_warn "apt-get update failed (attempt $attempt/$max_attempts), retrying in 5s..."
                sleep 5
            else
                log_warn "apt-get update failed after $max_attempts attempts, continuing anyway..."
            fi
        fi
        ((attempt++))
    done
fi

echo ""
log_header "Step 2: Node.js & npm"

if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    log_success "Node.js $NODE_VER already installed"
else
    log_warn "Node.js not found, installing..."
    if command -v sudo &>/dev/null; then
        sudo apt-get install -y -qq nodejs npm 2>/dev/null || \
        sudo apt-get install -y nodejs npm
        log_success "Node.js $(node --version) installed"
    else
        log_error "Node.js not installed and sudo not available"
        exit 1
    fi
fi

if ! command -v npm &>/dev/null; then
    log_error "npm not found in PATH after installation"
    exit 1
fi

NPM_VER=$(npm --version)
log_success "npm $NPM_VER is ready"

echo ""
log_header "Step 3: Codex CLI Installation"

# Ensure cache directory exists
mkdir -p "${CACHE_DIR}"
log_success "Cache directory: ${CACHE_DIR}"

# Install/update Codex
if "${ENSURE_SCRIPT}" --update 2>&1 | grep -E '(Installing|Updating|ERROR)'; then
    log_success "Codex CLI installation completed"
fi

CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_VERSION=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")

log_success "Codex binary: ${CODEX_BIN}"
log_success "Codex version: ${CODEX_VERSION}"

echo ""
log_header "Step 4: Verify Codex Works"

# Test basic codex command
if "${CODEX_BIN}" --help &>/dev/null; then
    log_success "Codex CLI responds to --help"
else
    log_warn "Codex --help check had issues (may still be functional)"
fi

echo ""
log_header "Step 5: WSL Proxy Configuration"

# Get Windows host IP
WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}' || echo "")

if [[ -z "$WIN_HOST_IP" ]]; then
    log_warn "Could not determine Windows host IP"
else
    log_success "Windows host IP detected: $WIN_HOST_IP"

    # Check if proxy is accessible
    if timeout 2 bash -c "echo > /dev/tcp/$WIN_HOST_IP/3128" 2>/dev/null; then
        log_success "Proxy accessible at $WIN_HOST_IP:3128"

        # Export proxy settings to current shell
        export http_proxy="http://${WIN_HOST_IP}:3128"
        export https_proxy="http://${WIN_HOST_IP}:3128"
        export HTTP_PROXY="$http_proxy"
        export HTTPS_PROXY="$https_proxy"

        log_success "Proxy environment variables exported for this session"
    else
        log_warn "Proxy not accessible at $WIN_HOST_IP:3128"
        log_warn "Run on Windows (PowerShell): python .\scripts\ops\wsl_proxy.py"
        log_warn "Or: .\scripts\ops\start-wsl-proxy.bat"
    fi
fi

echo ""
log_header "Step 6: Configure WSL Proxy Autoload"

BASHRC="$HOME/.bashrc"
WSL_PROXY_RC="${REPO_ROOT}/.wsl_proxy_env.sh"

if [[ ! -f "${WSL_PROXY_RC}" ]]; then
    log_warn "WSL proxy config not found: ${WSL_PROXY_RC}"
else
    if grep -q "wsl_proxy_env.sh" "${BASHRC}" 2>/dev/null; then
        log_success "WSL proxy auto-load already configured in ~/.bashrc"
    else
        log_warn "WSL proxy not configured for auto-load"
        echo ""
        echo "To enable automatic proxy configuration on shell startup, run:"
        echo ""
        echo "  echo 'source ${WSL_PROXY_RC}' >> ${BASHRC}"
        echo ""
        log_success "Add this line to enable auto-proxy in future sessions"
    fi
fi

echo ""
log_header "Step 7: Docker Connectivity Check"

if command -v docker.exe &>/dev/null; then
    log_success "docker.exe found (Windows Docker Desktop)"

    if docker.exe ps &>/dev/null; then
        log_success "Docker Desktop daemon is running"
    else
        log_warn "Docker Desktop daemon not responding"
        log_warn "Ensure Docker Desktop is running on Windows"
    fi
else
    log_warn "docker.exe not found in PATH"
    log_warn "Ensure Docker Desktop is installed and added to PATH"
fi

echo ""
echo "${SEPARATOR}"
echo "  Setup Complete!"
echo "${SEPARATOR}"
echo ""
echo "Next steps:"
echo ""
echo "1. Test interactive Codex:"
echo "   ${REPO_ROOT}/scripts/ops/launchers/codex/codex.sh"
echo ""
echo "2. Run Codex with a prompt:"
echo "   ${REPO_ROOT}/scripts/ops/launchers/codex/codex.sh \"analyze the pipeline\""
echo ""
echo "3. Run Codex in auto-exec mode:"
echo "   ${REPO_ROOT}/scripts/ops/launchers/codex/codex-exec.sh \"refactor ChemBL parser\""
echo ""
echo "4. From Windows (PowerShell), use the batch wrappers:"
echo "   .\scripts\ops\codex.bat"
echo "   .\scripts\ops\codex-exec.bat \"your prompt\""
echo ""
echo "5. Enable WSL proxy auto-load (optional):"
echo "   echo 'source ${WSL_PROXY_RC}' >> ${BASHRC}"
echo ""
echo "Documentation: ${REPO_ROOT}/docs/05-operations/"
echo ""
