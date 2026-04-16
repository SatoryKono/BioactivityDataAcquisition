#!/usr/bin/env bash
# Mistral - Main Entry Point (WSL/Linux)
# Usage: ./run-mistrall.sh [command] [args]

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

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Mistral - AI Model Server (via Ollama)"
echo "=================================================="
echo ""

# Show help
if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<EOF
Usage: ./run-mistrall.sh [command] [args]

Commands:
  (no args)      Start Mistral in interactive mode
  start          Start Mistral service in foreground
  daemon         Start Mistral as background service
  stop           Stop running Mistral service
  status         Check if Mistral is running
  logs           View Mistral service logs
  shell          Access Mistral container shell
  check          Check environment setup
  setup          Setup missing components (Docker, Ollama)
  pull           Pull latest Mistral model
  help           Show this help

Environment:
  MISTRALL_PORT  Service port (default: 11434)
  MISTRALL_MODEL Model name (default: mistral:latest)
  MISTRALL_MEMORY Memory allocation (default: 2g)
  DOCKER_BUILDKIT Enable build improvements (default: 1)

Examples:
  ./run-mistrall.sh
  ./run-mistrall.sh start
  ./run-mistrall.sh daemon
  ./run-mistrall.sh logs
  ./run-mistrall.sh shell

EOF
    exit 0
fi

# Check environment
log_info "Checking environment setup..."
echo ""

if ! bash "${HELPER_DIR}/check-env.sh" 2>/dev/null; then
    log_warn "Some components missing"
    log_info "Running setup to install/configure missing components..."
    echo ""
    
    if ! bash "${HELPER_DIR}/setup-env.sh"; then
        log_error "Setup failed"
        exit 1
    fi
fi

echo ""
log_info "Environment ready - launching Mistral"
echo ""

# Process command
COMMAND="${1:-start}"
shift || true

case "$COMMAND" in
    start|"")
        bash "${HELPER_DIR}/run-mistrall-impl.sh" start "$@"
        ;;
    
    daemon)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" daemon "$@"
        ;;
    
    stop)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" stop "$@"
        ;;
    
    status)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" status "$@"
        ;;
    
    logs)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" logs "$@"
        ;;
    
    shell)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" shell "$@"
        ;;
    
    pull)
        bash "${HELPER_DIR}/run-mistrall-impl.sh" pull "$@"
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
        log_info "Use './run-mistrall.sh help' for usage"
        exit 1
        ;;
esac

exit $?
