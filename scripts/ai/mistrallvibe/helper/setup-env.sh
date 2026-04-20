#!/usr/bin/env bash
# Helper: Setup Mistral Vibe environment
# Downloads and installs official Mistral Vibe

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
echo "  Mistral Vibe Setup"
echo "${SEPARATOR}"
echo ""

# Step 1: Check Python
log_info "STEP 1: Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
    log_error "Python3 is not installed"
    log_info "Install Python3: https://www.python.org/"
    exit 1
fi

PYTHON_VER=$(python3 --version)
log_success "Python ready: $PYTHON_VER"

# Step 2: Create .env.mistrallvibe
log_info "STEP 2: Creating .env.mistrallvibe..."
ENV_FILE="${ROOT_DIR}/.env.mistrallvibe"

if [[ -f "${ENV_FILE}" ]]; then
    log_success ".env.mistrallvibe already exists"
else
    cat > "${ENV_FILE}" <<'EOF'
# Mistral Vibe Configuration
VIBE_API_KEY=your-api-key-here
VIBE_PORT=5173
VIBE_HOST=localhost
EOF
    log_warn ".env.mistrallvibe created - please add your Mistral API key"
fi

echo ""

# Step 3: Install Mistral Vibe via pip or pipx
log_info "STEP 3: Installing Mistral Vibe..."
log_warn "This will install the official Mistral Vibe package"
echo ""

# Try pipx first (preferred)
if command -v pipx >/dev/null 2>&1; then
    log_info "Using pipx to install vibe"
    
    # Check if already installed
    if pipx list 2>/dev/null | grep -q mistral-vibe; then
        log_info "Upgrading existing mistral-vibe installation"
        if pipx upgrade mistral-vibe; then
            log_success "Mistral Vibe upgraded via pipx"
        else
            log_error "pipx upgrade failed"
            exit 1
        fi
    else
        log_info "Installing mistral-vibe for the first time"
        if pipx install mistral-vibe; then
            log_success "Mistral Vibe installed via pipx"
        else
            log_error "pipx installation failed"
            exit 1
        fi
    fi
else
    log_info "Using pip with --user flag"
    if python3 -m pip install --user --upgrade mistral-vibe; then
        log_success "Mistral Vibe installed via pip --user"
    else
        log_error "pip installation failed"
        log_info "Try installing pipx: sudo apt install pipx"
        exit 1
    fi
fi

echo ""

# Step 4: Fix PATH if needed
log_info "STEP 4: Checking PATH..."

# Ensure ~/.local/bin is in PATH
LOCAL_BIN="${HOME}/.local/bin"

if [[ -d "${LOCAL_BIN}" ]] && ! command -v vibe >/dev/null 2>&1; then
    log_warn "Adding ~/.local/bin to PATH"
    
    # Update bashrc
    if [[ -f "${HOME}/.bashrc" ]] && ! grep -q '.local/bin' "${HOME}/.bashrc"; then
        echo "" >> "${HOME}/.bashrc"
        echo "# Add local bin to PATH (added by vibe setup)" >> "${HOME}/.bashrc"
        echo "export PATH=\"${HOME}/.local/bin:\${PATH}\"" >> "${HOME}/.bashrc"
        log_success "Updated ~/.bashrc"
    fi
    
    # Update zshrc if exists
    if [[ -f "${HOME}/.zshrc" ]] && ! grep -q '.local/bin' "${HOME}/.zshrc"; then
        echo "" >> "${HOME}/.zshrc"
        echo "# Add local bin to PATH (added by vibe setup)" >> "${HOME}/.zshrc"
        echo "export PATH=\"${HOME}/.local/bin:\${PATH}\"" >> "${HOME}/.zshrc"
        log_success "Updated ~/.zshrc"
    fi
    
    # Apply to current session
    export PATH="${LOCAL_BIN}:${PATH}"
fi

# Verify vibe is accessible
if command -v vibe >/dev/null 2>&1; then
    VIBE_VERSION=$(vibe --version 2>/dev/null || echo "unknown")
    log_success "Vibe is ready: $VIBE_VERSION"
else
    log_warn "Vibe not found in PATH"
    log_info "Please restart your terminal or run:"
    echo "  export PATH=\"${HOME}/.local/bin:\${PATH}\""
fi

echo ""

# Step 5: Display next steps
echo "${SEPARATOR}"
log_success "Setup completed successfully!"
echo "${SEPARATOR}"
echo ""
log_info "Next steps:"
echo "  1. Get your API key: https://console.mistral.ai/api-keys/"
echo "  2. Edit .env.mistrallvibe and add VIBE_API_KEY"
echo "  3. Start Vibe: ./run-vibe.sh"
echo "  4. Or run with a prompt: ./run-vibe.sh \"inspect the failing tests\""
echo ""

if ! command -v vibe >/dev/null 2>&1; then
    log_warn "If 'vibe' command not found, restart your terminal"
    echo "  Or run: export PATH=\"${HOME}/.local/bin:\${PATH}\""
fi

echo ""

exit 0
