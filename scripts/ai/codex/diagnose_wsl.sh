#!/usr/bin/env bash
# Canonical Codex WSL diagnostic tool.

set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'EOF'
Codex WSL Diagnostic Tool

Usage: bash scripts/ai/codex/diagnose_wsl.sh

Checks environment, Node/npm, Codex bootstrap, permissions, Docker,
proxy, and basic network connectivity for the Codex-on-WSL workflow.
EOF
    exit 0
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Codex WSL Diagnostic Tool                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"

header "1. Environment"

if grep -qi microsoft /proc/version 2>/dev/null; then
    check_pass "Running in WSL"
else
    check_fail "Not running in WSL"
fi

if command -v bash &>/dev/null; then
    check_pass "Bash available: $(bash --version 2>&1 | head -1)"
else
    check_fail "Bash not found"
fi

header "2. Node.js & npm"

if command -v node &>/dev/null; then
    check_pass "Node.js $(node --version) installed"
else
    check_fail "Node.js not found in PATH"
fi

if command -v npm &>/dev/null; then
    check_pass "npm $(npm --version) installed"
    check_pass "npm prefix: $(npm config get prefix 2>/dev/null || echo "unknown")"
else
    check_fail "npm not found in PATH"
fi

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

header "5. Launch Scripts"

for script in \
    "${SCRIPT_DIR}/launch.sh" \
    "${SCRIPT_DIR}/exec.sh" \
    "${REPO_ROOT}/script-codex/helper/setup-wsl-complete.sh"; do
    script_name="$(basename "${script}")"
    if [[ -f "${script}" ]]; then
        if [[ -x "${script}" ]] 2>/dev/null || file "${script}" | grep -q "shell script"; then
            check_pass "Script available: ${script_name}"
        else
            check_warn "Script exists but may not be executable: ${script_name}"
        fi
    else
        check_fail "Script not found: ${script_name}"
    fi
done

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

header "7. Network & Proxy"

WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}' || echo "")
if [[ -n "${WIN_HOST_IP}" ]]; then
    check_pass "Windows host IP: ${WIN_HOST_IP}"
    if timeout 2 bash -c "echo > /dev/tcp/${WIN_HOST_IP}/3128" 2>/dev/null; then
        check_pass "Proxy accessible at ${WIN_HOST_IP}:3128"
    else
        check_warn "Proxy not accessible at ${WIN_HOST_IP}:3128 (may not be running)"
    fi
else
    check_fail "Could not determine Windows host IP"
fi

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

header "8. External Connectivity"

if timeout 5 curl -s --connect-timeout 3 https://www.google.com &>/dev/null; then
    check_pass "Internet connectivity: OK"
elif timeout 5 curl -s --connect-timeout 3 http://www.google.com &>/dev/null; then
    check_pass "Internet connectivity: OK (HTTP)"
else
    check_warn "Could not reach google.com (proxy issue or offline)"
fi

if timeout 5 curl -s --connect-timeout 3 https://registry.npmjs.org/npm &>/dev/null; then
    check_pass "npm registry accessible: OK"
else
    check_warn "Could not reach npm registry (proxy issue or offline)"
fi

summary

if [[ ${FAIL} -gt 0 ]]; then
    echo -e "${RED}Critical Issues Found:${NC}"
    echo ""
    if ! command -v node >/dev/null 2>&1; then
        echo "  • Install Node.js: sudo apt-get install -y nodejs npm"
    fi
fi

exit "${FAIL}"
