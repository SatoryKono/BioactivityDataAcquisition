#!/usr/bin/env bash
# Gemini - Main Entry Point (WSL)
# Usage: ./run-gemini.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[OK]${NC} ${message}"
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
echo "=================================================="
echo "  Gemini - Google AI Assistant"
echo "=================================================="
echo ""

# Show help
if [[ "${1:-}" =~ ^(help|-h|--help)$ ]]; then
    cat <<EOF
Usage: ./run-gemini.sh [command] [prompt]

Commands:
  (no args)      Start interactive Gemini
  start          Start interactive mode
  prompt         Send a single prompt
  exec           Auto-execute in headless mode (YOLO approvals)
  check          Check environment setup
  setup          Setup missing components
  mcp-check      Check Gemini MCP configuration
  mcp-setup      Sync Gemini MCP configuration
  update         Update managed Gemini runtime
  help           Show this help

Examples:
  ./run-gemini.sh
  ./run-gemini.sh "what is AI?"
  ./run-gemini.sh prompt "explain this repository"
  ./run-gemini.sh exec "fix formatting issues"
  ./run-gemini.sh "explain quantum computing"

EOF
    exit 0
fi

COMMAND="${1:-start}"

case "${COMMAND}" in
    check)
        bash "${HELPER_DIR}/check-env.sh"
        exit $?
        ;;
    setup)
        log_info "Running setup (this may take 2-3 minutes)..."
        log_warn "DO NOT CLOSE THIS WINDOW"
        echo ""

        bash "${HELPER_DIR}/setup-env.sh"
        setupExit=$?

        echo ""
        if [[ $setupExit -eq 0 ]]; then
            log_success "Setup completed!"
            log_info "Now run: ./run-gemini.sh"
        else
            log_error "Setup failed with exit code: $setupExit"
            log_info "Check system logs for details"
        fi
        exit $setupExit
        ;;
    mcp-check)
        bash "${HELPER_DIR}/ensure-mcp.sh" --check
        exit $?
        ;;
    mcp-setup)
        bash "${HELPER_DIR}/ensure-mcp.sh" --ensure
        exit $?
        ;;
    update)
        bash "${HELPER_DIR}/ensure-gemini-cli.sh" --update
        exit $?
        ;;
    *)
        ;;
esac

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

# Process command
shift || true

case "$COMMAND" in
    start|"")
        log_info "Launching Gemini..."
        echo ""
        bash "${HELPER_DIR}/run-gemini-impl.sh" "$@"
        ;;

    prompt)
        if [[ $# -eq 0 ]]; then
            log_error "prompt mode requires a prompt"
            exit 1
        fi
        log_info "Launching Gemini with prompt..."
        echo ""
        bash "${HELPER_DIR}/run-gemini-impl.sh" --prompt "$*"
        ;;

    exec)
        if [[ $# -eq 0 ]]; then
            log_error "exec mode requires a prompt"
            exit 1
        fi
        log_info "Launching Gemini in headless auto-execute mode..."
        echo ""
        bash "${HELPER_DIR}/run-gemini-impl.sh" --prompt "$*" --approval-mode yolo
        ;;

    *)
        # Treat first arg as prompt
        log_info "Launching Gemini with prompt..."
        echo ""
        bash "${HELPER_DIR}/run-gemini-impl.sh" --prompt "$COMMAND $*"
        ;;
esac

exit $?
