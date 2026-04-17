#!/usr/bin/env bash
# Codex - Main Entry Point (WSL)
# Usage: ./run-codex.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[⚠]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}[✗]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

echo ""
echo "=================================================="
echo "  Codex - AI Code Assistant"
echo "=================================================="
echo ""

# Show help
if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<EOF
Usage: ./run-codex.sh [command] [prompt]

Commands:
  (no args)      Start interactive Codex
  start          Start interactive mode
  exec           Auto-execute (no confirmations)
  login          Login with API key
  device-login   Login with device auth
  check          Check environment setup
  setup          Setup missing components
  help           Show this help

Examples:
  ./run-codex.sh
  ./run-codex.sh "analyze the code"
  ./run-codex.sh exec "refactor the parser"
  ./run-codex.sh login

EOF
    exit 0
fi

# Check environment
log_info "Checking environment setup..."
echo ""

if ! bash "${HELPER_DIR}/check-env.sh" 2>/dev/null; then
    log_warn "Some components missing"
    log_info "Running setup to install missing components..."
    echo ""
    
    if ! bash "${HELPER_DIR}/setup-env.sh"; then
        log_error "Setup failed"
        exit 1
    fi
fi

echo ""
log_info "Environment ready - launching Codex"
echo ""

# Process command
COMMAND="${1:-start}"
shift || true

case "$COMMAND" in
    start|"")
        bash "${HELPER_DIR}/run-codex-impl.sh" "$@"
        ;;
    
    exec)
        if [[ $# -eq 0 ]]; then
            log_error "exec mode requires a prompt"
            exit 1
        fi
        bash "${HELPER_DIR}/run-codex-impl.sh" exec --full-auto "$@"
        ;;
    
    login)
        codex login
        ;;
    
    device-login)
        codex login --device-auth
        ;;
    
    check)
        bash "${HELPER_DIR}/check-env.sh"
        exit 0
        ;;
    
    setup)
        bash "${HELPER_DIR}/setup-env.sh"
        exit $?
        ;;
    
    *)
        # Treat as prompt
        bash "${HELPER_DIR}/run-codex-impl.sh" "$COMMAND" "$@"
        ;;
esac

exit $?
