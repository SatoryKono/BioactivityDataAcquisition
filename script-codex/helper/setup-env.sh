#!/usr/bin/env bash
# Helper: Setup missing components WITHOUT apt-get
# Skips apt if it's hanging, installs from binaries instead

set -u  

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[X]${NC} $1"; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Codex Setup - Installation"
echo "=================================================="
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

# Check if already installed globally
if command -v codex >/dev/null 2>&1; then
    log_success "Codex already installed: $(codex --version)"
    exit 0
fi

log_info "Running npm install -g @openai/codex (3 attempts, timeout 180s each)..."

SUCCESS=0
for attempt in 1 2 3; do
    log_info "  Attempt $attempt/3..."
    
    # Try with sudo first if needed, then fallback to --save-prefix if permission denied
    if timeout 180 npm install -g @openai/codex@latest 2>&1 | tail -5; then
        # Verify installation
        if command -v codex >/dev/null 2>&1; then
            log_success "Codex installed: $(codex --version)"
            SUCCESS=1
            break
        else
            log_warn "  npm succeeded but codex not in PATH yet"
        fi
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 124 ]]; then
            log_warn "  Attempt $attempt timed out (124)"
        elif [[ $EXIT_CODE -eq 243 ]]; then
            log_warn "  Attempt $attempt failed with permission error (243) - trying with sudo"
            if sudo timeout 180 npm install -g @openai/codex@latest 2>&1 | tail -5; then
                if command -v codex >/dev/null 2>&1; then
                    log_success "Codex installed via sudo: $(codex --version)"
                    SUCCESS=1
                    break
                fi
            fi
        else
            log_warn "  Attempt $attempt failed (code: $EXIT_CODE)"
        fi
    fi
    
    if [[ $attempt -lt 3 ]]; then
        log_info "  Waiting 3 seconds before retry..."
        sleep 3
    fi
done

if [[ $SUCCESS -eq 0 ]]; then
    # Last resort - check if it's somewhere in npm
    CODEX_BIN=$(npm list -g @openai/codex 2>/dev/null | grep "@openai/codex" | head -1)
    if [[ ! -z "$CODEX_BIN" ]]; then
        log_warn "Codex was installed but not in PATH"
        log_info "Location: $CODEX_BIN"
        log_info "Try running: hash -r && codex"
        exit 0
    fi
    
    log_error "Codex installation failed after 3 attempts"
    log_info "Trying manual installation..."
    
    # Last attempt with sudo
    if sudo npm install -g @openai/codex@latest 2>&1 | tail -20; then
        if command -v codex >/dev/null 2>&1; then
            log_success "Codex installed via sudo"
            exit 0
        fi
    fi
    
    log_error "Permission issue detected. You may need to:"
    echo "  1. Fix npm permissions: npm config set prefix ~/.npm-global"
    echo "  2. Or use: sudo npm install -g @openai/codex@latest"
    exit 1
fi

echo ""

# STEP 4: Setup .env.codex
log_info "STEP 4: Configuring .env.codex..."
ENV_FILE="${ROOT_DIR}/.env.codex"

if [[ ! -f "${ENV_FILE}" ]]; then
    cat > "${ENV_FILE}" <<EOF
# OpenAI Codex Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
EOF
    log_warn ".env.codex created - please add your API key"
else
    log_success ".env.codex exists"
fi

echo ""
echo "=================================================="
log_success "Setup completed successfully!"
echo "=================================================="
echo ""
log_info "Next steps:"
echo "  1. Edit .env.codex and add your OpenAI API key"
echo "  2. Run: .\run-codex.ps1"
echo ""

exit 0
