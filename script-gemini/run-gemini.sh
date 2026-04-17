#!/usr/bin/env bash
# Gemini - Main Entry Point (WSL)
# Usage: ./run-gemini.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1}"
    echo -e "${GREEN}[OK]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1}"
    echo -e "${YELLOW}[!]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1}"
    echo -e "${RED}[X]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1}"
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
  check          Check environment setup
  setup          Setup missing components
  help           Show this help

Examples:
  ./run-gemini.sh
  ./run-gemini.sh "what is AI?"
  ./run-gemini.sh "explain quantum computing"

EOF
    exit 0
fi

# Check environment without blocking
log_info "Checking environment..."

# Quick Python3 check
PYTHON_OK=false
if command -v python3 >/dev/null 2>&1; then
    log_success "Python3 found"
    PYTHON_OK=true
else
    log_warn "Python3 not found"
fi

# Quick google-generativeai check
GEMINI_OK=false
PYTHON_BIN="python3"
VENV_DIR="${HOME}/.cache/tools/gemini-venv"
if [[ -x "${VENV_DIR}/bin/python" ]]; then
    PYTHON_BIN="${VENV_DIR}/bin/python"
fi

if "${PYTHON_BIN}" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('google.genai') or importlib.util.find_spec('google.generativeai') else 1)" 2>/dev/null; then
    log_success "Gemini Python SDK found"
    GEMINI_OK=true
else
    log_warn "Gemini Python SDK not found"
fi

echo ""

# If anything missing and not already running setup
if { [[ "$PYTHON_OK" == "false" ]] || [[ "$GEMINI_OK" == "false" ]]; } && [[ "${1:-}" != "setup" ]]; then
    log_warn "Some components missing"
    log_info "Run setup first: ./run-gemini.sh setup"
    echo ""
    exit 1
fi

# Process command
COMMAND="${1:-start}"
shift || true
PROMPT="$@"

case "$COMMAND" in
    start|"")
        log_info "Launching Gemini..."
        echo ""
        if [[ -n "$PROMPT" ]]; then
            bash "${HELPER_DIR}/run-gemini-impl.sh" -- "$PROMPT"
        else
            bash "${HELPER_DIR}/run-gemini-impl.sh"
        fi
        ;;
    
    check)
        bash "${HELPER_DIR}/check-env.sh"
        exit 0
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
    
    *)
        # Treat first arg as prompt
        log_info "Launching Gemini with prompt..."
        echo ""
        bash "${HELPER_DIR}/run-gemini-impl.sh" -- "$COMMAND" "$PROMPT"
        ;;
esac

exit $?
