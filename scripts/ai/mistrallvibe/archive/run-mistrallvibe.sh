#!/usr/bin/env bash
# Mistral-Vibe - Main Entry Point (WSL/Linux)
# Usage: ./run-mistrallvibe.sh [command] [args]
# Official Mistral Vibe - https://mistral.ai/vibe/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-.}"

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
echo "  Mistral Vibe - Official Web UI"
echo "=================================================="
echo ""

# Show help
if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<EOF
Usage: ./run-mistrallvibe.sh [command] [args]

Commands:
  (no args)      Start Mistral Vibe
  start          Start Vibe server
  stop           Stop Vibe server
  status         Check Vibe status
  logs           View Vibe logs
  browser        Open browser to Vibe UI
  chat|cli       Interactive chat in console
  api-key        Show API key
  check          Check environment setup
  setup          Install Mistral Vibe
  help           Show this help

Configuration:
  Edit .env.mistrallvibe for:
  - VIBE_API_KEY       Your Mistral API key
  - VIBE_PORT          Server port (default: 5173)
  - VIBE_HOST          Server host (default: localhost)

Examples:
  ./run-mistrallvibe.sh setup    # First time setup
  ./run-mistrallvibe.sh start    # Start server
  ./run-mistrallvibe.sh api-key  # View your API key

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
log_info "Environment ready - launching Mistral Vibe"
echo ""

# Process command
COMMAND="${1:-start}"
shift || true

case "$COMMAND" in
    start|"")
        cd "${SCRIPT_DIR}"
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" start "$@"
        ;;
    
    stop)
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" stop "$@"
        ;;
    
    status)
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" status "$@"
        ;;
    
    logs)
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" logs "$@"
        ;;
    
    browser)
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" browser "$@"
        ;;
    
    chat|cli)
        cd "${SCRIPT_DIR}"
        exec python3 "${SCRIPT_DIR}/vibe-cli.py" "$@"
        ;;
    
    api-key)
        exec bash "${HELPER_DIR}/run-mistrallvibe-impl.sh" api-key "$@"
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
        log_error "Unknown command: $COMMAND"
        log_info "Use './run-mistrallvibe.sh help' for usage"
        exit 1
        ;;
esac

exit $?
