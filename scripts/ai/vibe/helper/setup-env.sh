#!/usr/bin/env bash
# Helper: Setup Mistral Vibe environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
echo "  Mistral Vibe Setup"
echo "${SEPARATOR}"
echo ""

log_info "STEP 1: Checking Python..."
if timeout 10 bash -c "command -v python3 >/dev/null 2>&1"; then
    PYTHON_VER=$(timeout 5 python3 --version 2>/dev/null || echo "unknown")
    log_success "Python ready: $PYTHON_VER"
else
    log_error "Python3 is not installed"
    exit 1
fi

log_info "STEP 2: Checking .env.vibe..."
ENV_FILE="${ROOT_DIR}/.env.vibe"
if [[ -f "${ENV_FILE}" ]]; then
    log_success ".env.vibe already exists"
else
    if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" != "1" ]]; then
        log_warn ".env.vibe not found; not creating it without BIOETL_CREATE_LOCAL_ENV_FILES=1"
        log_info "Create ${ENV_FILE} manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to generate a local template."
    else
        log_warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.vibe template"
        cat > "${ENV_FILE}" <<'EOF'
# Mistral Vibe Configuration
MISTRAL_API_KEY=your-api-key-here
# Legacy compatibility alias:
# VIBE_API_KEY=your-api-key-here
EOF
        log_warn ".env.vibe created - please add your Mistral API key"
    fi
fi

echo ""
log_info "STEP 3: Installing Mistral Vibe..."

INSTALL_SUCCESS=0
RETRY_COUNT=0
MAX_RETRIES=2

if timeout 10 bash -c "command -v pipx >/dev/null 2>&1"; then
    log_info "Using pipx to install vibe"
    if timeout 10 pipx list 2>/dev/null | grep -q mistral-vibe 2>/dev/null; then
        while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
            if timeout 60 pipx upgrade mistral-vibe 2>/dev/null; then
                log_success "Mistral Vibe upgraded via pipx"
                INSTALL_SUCCESS=1
                break
            fi
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; then
                log_warn "pipx upgrade failed (attempt ${RETRY_COUNT}/${MAX_RETRIES}), retrying..."
                sleep 2
            fi
        done
    else
        while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
            if timeout 60 pipx install mistral-vibe 2>/dev/null; then
                log_success "Mistral Vibe installed via pipx"
                INSTALL_SUCCESS=1
                break
            fi
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; then
                log_warn "pipx install failed (attempt ${RETRY_COUNT}/${MAX_RETRIES}), retrying..."
                sleep 2
            fi
        done
    fi
fi

if [[ ${INSTALL_SUCCESS} -eq 0 ]]; then
    RETRY_COUNT=0
    while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
        if timeout 60 python3 -m pip install --user --upgrade mistral-vibe 2>/dev/null; then
            log_success "Mistral Vibe installed via pip --user"
            INSTALL_SUCCESS=1
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; then
            log_warn "pip install failed (attempt ${RETRY_COUNT}/${MAX_RETRIES}), retrying..."
            sleep 2
        fi
    done
fi

if [[ ${INSTALL_SUCCESS} -eq 0 ]]; then
    log_error "Installation failed after all retries"
    exit 1
fi

echo ""
echo "${SEPARATOR}"
log_success "Setup completed successfully!"
echo "${SEPARATOR}"
echo ""
log_info "Next steps:"
echo "  1. Create or edit scripts/ai/vibe/.env.vibe and add MISTRAL_API_KEY"
echo "     To generate a local template, rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1"
echo "  2. Verify setup: python -m scripts.ai vibe check"
echo "  3. Start Vibe: python -m scripts.ai vibe"
echo ""
