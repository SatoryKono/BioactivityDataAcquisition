#!/usr/bin/env bash
# Gemini - Main Entry Point (WSL)
# Usage: ./run-gemini.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../..")}"

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

ensure_env_template() {
    local env_file="${SCRIPT_DIR}/.env.gemini"
    local repo_env_file="${REPO_ROOT}/.env.gemini"

    if [[ -f "${env_file}" ]]; then
        return 0
    fi

    log_warn ".env.gemini not found, checking repo root..."
    if [[ -f "${repo_env_file}" ]]; then
        return 0
    fi

    log_warn "Creating .env.gemini in scripts/ai/gemini/..."
    cat > "${env_file}" <<'ENVEOF'
# Google Gemini CLI Configuration
# Get your API key from: https://aistudio.google.com/app/apikeys
GEMINI_API_KEY=your-api-key-here
# Optional model override
# GEMINI_MODEL=gemini-2.5-flash
ENVEOF
    log_error "Please edit ${env_file} and add your Gemini API key"
    exit 1
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

RETRY_COUNT=0
MAX_RETRIES=2

while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
    if bash "${HELPER_DIR}/check-env.sh" 2>/dev/null; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))

    if [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; then
        log_warn "Some components missing (attempt ${RETRY_COUNT}/${MAX_RETRIES})"
        log_info "Running setup to install missing components..."
        echo ""

        if ! bash "${HELPER_DIR}/setup-env.sh"; then
            log_error "Setup failed on attempt ${RETRY_COUNT}"
            exit 1
        fi
        echo ""
    fi
done

if [[ ${RETRY_COUNT} -eq ${MAX_RETRIES} ]]; then
    log_error "Environment check failed after ${MAX_RETRIES} attempts"
    exit 1
fi

echo ""
log_info "Environment ready - launching Gemini"
echo ""

ensure_env_template

# Process command
shift || true

case "$COMMAND" in
    start|"")
        log_info "Launching Gemini..."
        echo ""
        if [[ "${GEMINI_INTERACTIVE_ALL_MCP:-0}" == "1" ]]; then
            bash "${HELPER_DIR}/run-gemini-impl.sh" "$@"
        else
            GEMINI_INTERACTIVE_MCP_SERVERS="${GEMINI_INTERACTIVE_MCP_SERVERS:-memory,filesystem}"
            log_info "Fast interactive MCP allowlist: ${GEMINI_INTERACTIVE_MCP_SERVERS}"
            log_info "Set GEMINI_INTERACTIVE_ALL_MCP=1 to enable every configured MCP server."
            bash "${HELPER_DIR}/run-gemini-impl.sh" --allowed-mcp-server-names "${GEMINI_INTERACTIVE_MCP_SERVERS}" "$@"
        fi
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
        if [[ $# -gt 0 ]]; then
            bash "${HELPER_DIR}/run-gemini-impl.sh" --prompt "${COMMAND} $*"
        else
            bash "${HELPER_DIR}/run-gemini-impl.sh" --prompt "${COMMAND}"
        fi
        ;;
esac

exit $?
