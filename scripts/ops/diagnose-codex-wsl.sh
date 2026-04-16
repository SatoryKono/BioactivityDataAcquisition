#!/usr/bin/env bash
# Codex WSL Diagnostic Tool
# Checks system configuration and Codex setup status
# Usage: bash ./scripts/ops/diagnose-codex-wsl.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASS=0
WARN=0
FAIL=0

check_pass() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASS++))
}

check_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    ((WARN++))
}

check_fail() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAIL++))
}

header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Summary: ${GREEN}$PASS passed${NC} | ${YELLOW}$WARN warnings${NC} | ${RED}$FAIL failed${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Setup paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Codex WSL Diagnostic Tool                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# ==================== ENVIRONMENT ====================
header "1. Environment"

# Check WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    check_pass "Running in WSL"
else
    check_fail "Not running in WSL"
fi

# Check bash version
if command -v bash &>/dev/null; then
    BASH_VER=$(bash --version 2>&1 | head -1)
    check_pass "Bash available: $BASH_VER"
else
    check_fail "Bash not found"
fi

# ==================== NODEJS ====================
header "2. Node.js & npm"

if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    check_pass "Node.js $NODE_VER installed"
else
    check_fail "Node.js not found in PATH"
fi

if command -v npm &>/dev/null; then
    NPM_VER=$(npm --version)
    check_pass "npm $NPM_VER installed"
    
    # Check npm prefix
    NPM_PREFIX=$(npm config get prefix 2>/dev/null || echo "unknown")
    check_pass "npm prefix: $NPM_PREFIX"
else
    check_fail "npm not found in PATH"
fi

# ==================== CODEX ====================
header "3. Codex Installation"

if [[ -f "${ENSURE_SCRIPT}" ]]; then
    check_pass "Ensure script found: ${ENSURE_SCRIPT}"
else
    check_fail "Ensure script not found: ${ENSURE_SCRIPT}"
fi

if [[ -x "${ENSURE_SCRIPT}" ]]; then
    check_pass "Ensure script is executable"
else
    check_warn "Ensure script is not executable"
fi

# Try to get Codex binary path
if CODEX_BIN=$("${ENSURE_SCRIPT}" --print-bin 2>/dev/null); then
    if [[ -x "${CODEX_BIN}" ]]; then
        check_pass "Codex binary found: ${CODEX_BIN}"
        
        if CODEX_VER=$("${CODEX_BIN}" --version 2>/dev/null); then
            check_pass "Codex version: ${CODEX_VER}"
        else
            check_warn "Could not determine Codex version"
        fi
    else
        check_warn "Codex binary not executable: ${CODEX_BIN}"
    fi
else
    check_warn "Codex not yet installed (will be installed on first use)"
fi

# ==================== PATHS ====================
header "4. Paths & Permissions"

check_pass "Repository: ${REPO_ROOT}"

CACHE_DIR="${REPO_ROOT}/.cache/tools"
if [[ -d "${CACHE_DIR}" ]]; then
    check_pass "Cache directory exists: ${CACHE_DIR}"
else
    check_warn "Cache directory missing (will be created): ${CACHE_DIR}"
fi

if [[ -w "${REPO_ROOT}" ]]; then
    check_pass "Repository is writable"
else
    check_fail "Repository is not writable"
fi

if [[ -w "${HOME}" ]]; then
    check_pass "Home directory is writable"
else
    check_fail "Home directory is not writable"
fi

# ==================== SCRIPTS ====================
header "5. Launch Scripts"

for script in \
    "${SCRIPT_DIR}/codex.sh" \
    "${SCRIPT_DIR}/codex-exec.sh" \
    "${REPO_ROOT}/script-codex/helper/setup-wsl-complete.sh"; do
    SCRIPT_PATH="${script}"
    SCRIPT_NAME="$(basename "${SCRIPT_PATH}")"
    if [[ -f "${SCRIPT_PATH}" ]]; then
        if [[ -x "${SCRIPT_PATH}" ]] 2>/dev/null || file "${SCRIPT_PATH}" | grep -q "shell script"; then
            check_pass "Script available: ${SCRIPT_NAME}"
        else
            check_warn "Script exists but may not be executable: ${SCRIPT_NAME}"
        fi
    else
        check_fail "Script not found: ${SCRIPT_NAME}"
    fi
done

# ==================== DOCKER ====================
header "6. Docker Connectivity"

if command -v docker &>/dev/null; then
    check_pass "docker CLI found (WSL Docker)"
else
    check_warn "docker CLI not found (WSL)"
fi

if command -v docker.exe &>/dev/null; then
    check_pass "docker.exe found (Windows Docker Desktop)"
    
    if docker.exe ps &>/dev/null 2>&1; then
        check_pass "Docker Desktop daemon is running"
    else
        check_warn "Docker Desktop daemon not responding"
    fi
else
    check_warn "docker.exe not found (ensure Docker Desktop is running)"
fi

# ==================== NETWORK ====================
header "7. Network & Proxy"

# Get Windows host IP
WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}' || echo "")

if [[ -n "$WIN_HOST_IP" ]]; then
    check_pass "Windows host IP: $WIN_HOST_IP"
    
    # Check proxy
    if timeout 2 bash -c "echo > /dev/tcp/$WIN_HOST_IP/3128" 2>/dev/null; then
        check_pass "Proxy accessible at $WIN_HOST_IP:3128"
    else
        check_warn "Proxy not accessible at $WIN_HOST_IP:3128 (may not be running)"
    fi
else
    check_fail "Could not determine Windows host IP"
fi

# Check proxy environment variables
if [[ -n "${http_proxy:-}" ]]; then
    check_pass "http_proxy set: ${http_proxy}"
else
    check_warn "http_proxy not set (proxy not configured for this session)"
fi

if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    check_pass "WSL proxy config file found: .wsl_proxy_env.sh"
else
    check_warn "WSL proxy config file not found: .wsl_proxy_env.sh"
fi

# ==================== CONNECTIVITY ====================
header "8. External Connectivity"

# Test internet access
if timeout 5 curl -s --connect-timeout 3 https://www.google.com &>/dev/null; then
    check_pass "Internet connectivity: OK"
elif timeout 5 curl -s --connect-timeout 3 http://www.google.com &>/dev/null; then
    check_pass "Internet connectivity: OK (HTTP)"
else
    check_warn "Could not reach google.com (proxy issue or offline)"
fi

# Test npm registry
if timeout 5 curl -s --connect-timeout 3 https://registry.npmjs.org/npm &>/dev/null; then
    check_pass "npm registry accessible: OK"
else
    check_warn "Could not reach npm registry (proxy issue or offline)"
fi

# ==================== SUMMARY ====================
summary

# ==================== RECOMMENDATIONS ====================

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}Critical Issues Found:${NC}"
    echo ""
    
    if [[ ! -v NODE_VER ]]; then
        echo "  • Install Node.js: sudo apt-get install -y nodejs npm"
    fi
    
    if [[ $FAIL -gt 0 ]]; then
        echo "  • Address failed checks above before using Codex"
    fi
    
    echo ""
fi

if [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}Warnings (Optional):${NC}"
    echo ""
    
    if [[ -z "${WIN_HOST_IP}" ]]; then
        echo "  • Could not detect Windows host IP (proxy may not work)"
    fi
    
    if grep -q "Proxy not accessible" <<EOF
check_warn calls
EOF
    then
        echo "  • Start proxy on Windows: .\scripts\ops\start-wsl-proxy.bat"
    fi
    
    echo ""
fi

if [[ $PASS -gt 0 ]]; then
    echo -e "${GREEN}System appears ready to run Codex!${NC}"
    echo ""
    echo "Quick start:"
    echo "  ./scripts/ops/codex.sh"
    echo "  ./scripts/ops/codex.sh \"your prompt\""
    echo "  ./scripts/ops/codex-exec.sh \"your prompt\""
    echo ""
fi

# Exit with appropriate code
if [[ $FAIL -gt 0 ]]; then
    exit 1
elif [[ $WARN -gt 0 ]]; then
    exit 0
else
    exit 0
fi
