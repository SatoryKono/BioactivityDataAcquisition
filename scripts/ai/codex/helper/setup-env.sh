#!/usr/bin/env bash
# Helper: Setup missing components WITHOUT apt-get
# Skips apt if it's hanging, installs from binaries instead

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${SCRIPT_DIR}/ensure-mcp.sh"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
SEPARATOR="=================================================="

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
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
echo "  Codex Setup - Installation"
echo "${SEPARATOR}"
echo ""

# STEP 1: Check Node.js
log_info "STEP 1: Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    log_success "Node.js found: $(node --version)"
    NODE_EXISTS=1
else
    log_warn "Node.js NOT found"
    NODE_EXISTS=0
fi

# STEP 2: Check npm
log_info "STEP 2: Checking npm..."
if command -v npm >/dev/null 2>&1; then
    log_success "npm found: $(npm --version)"
    NPM_EXISTS=1
else
    log_warn "npm NOT found"
    NPM_EXISTS=0
fi

echo ""

# If both exist, skip to Codex
if [[ $NODE_EXISTS -eq 1 ]] && [[ $NPM_EXISTS -eq 1 ]]; then
    log_success "Node.js and npm already installed, skipping..."
else
    log_warn "Node.js or npm missing - cannot install Codex without them"
    exit 1
fi

echo ""

# STEP 3: Install Codex
log_info "STEP 3: Installing Codex CLI..."
if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    log_error "Bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

CODEX_BIN=""
if CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null)" && [[ -x "${CODEX_BIN}" ]]; then
    log_success "Codex already installed: $(timeout 5 "${CODEX_BIN}" --version 2>/dev/null || echo 'version check timeout')"
else
    log_info "Installing managed Codex CLI into repo-local prefix..."
    if ! timeout 120 "${ENSURE_SCRIPT}" --ensure >/dev/null 2>&1; then
        log_error "Codex installation failed or timed out"
        exit 1
    fi
    CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --print-bin 2>/dev/null || echo "")"
    if [[ -z "${CODEX_BIN}" ]]; then
        log_error "Could not determine Codex binary path"
        exit 1
    fi
    log_success "Codex installed: $(timeout 5 "${CODEX_BIN}" --version 2>/dev/null || echo 'version check timeout')"
fi

echo ""

# STEP 4: Auth surface (.env.codex optional when ChatGPT device auth exists)
# shellcheck source=codex-auth-lib.sh
source "${SCRIPT_DIR}/codex-auth-lib.sh"
log_info "STEP 4: Checking Codex authentication..."
ENV_FILE="${ROOT_DIR}/.env.codex"

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
    log_success ".env.codex exists"
elif [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" == "1" ]]; then
    log_warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.codex template"
    cat > "${ENV_FILE}" <<'ENVEOF'
# OpenAI Codex Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
ENVEOF
    log_warn ".env.codex created - please add your API key (or use device-login instead)"
else
    log_info ".env.codex not found; ChatGPT device auth in ~/.codex/auth.json is enough"
fi

if codex_has_usable_auth; then
    log_success "Usable auth: $(codex_auth_status_label)"
else
    log_warn "No usable auth yet — run device-login or add OPENAI_API_KEY"
fi

echo ""

# STEP 5: Setup MCP
log_info "STEP 5: Configuring MCP for Codex..."
if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
    log_error "MCP helper not found: ${ENSURE_MCP_SCRIPT}"
    exit 1
fi

if timeout 30 bash -c "CODEX_BIN='${CODEX_BIN}' '${ENSURE_MCP_SCRIPT}' --ensure --codex-bin '${CODEX_BIN}'" >/dev/null 2>&1; then
    log_success "MCP configuration synchronized"
else
    log_error "MCP configuration failed or timed out"
    exit 1
fi

echo ""
echo "${SEPARATOR}"
log_success "Setup completed successfully!"
echo "${SEPARATOR}"
echo ""
log_info "Next steps (WSL):"
echo "  1. If needed: bash scripts/ai/codex/run-codex.sh device-login"
echo "  2. Interactive: bash scripts/ai/codex/run-codex.sh"
echo "  3. Or from repo: codex   (bashrc wrapper → scripts/ops/launchers/codex/codex.sh)"
echo ""

exit 0
