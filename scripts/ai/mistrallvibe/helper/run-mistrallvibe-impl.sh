#!/usr/bin/env bash
# Helper: Run Mistral Vibe operations
# Historical manager helper retained for compatibility only.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

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

# Load environment
ENV_FILE="${ROOT_DIR}/.env.mistrallvibe"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

VIBE_PORT="${VIBE_PORT:-5173}"
VIBE_HOST="${VIBE_HOST:-localhost}"
if [[ -n "${MISTRAL_API_KEY:-}" && -z "${VIBE_API_KEY:-}" ]]; then
    VIBE_API_KEY="${MISTRAL_API_KEY}"
else
    VIBE_API_KEY="${VIBE_API_KEY:-}"
fi
SERVER_SCRIPT="${ROOT_DIR}/vibe-server.js"
SERVER_PROCESS_PATTERN="vibe-server.js"

# Function: Start Vibe server
start_vibe() {
    log_info "Starting Mistral Vibe Server..."

    if [[ -z "${VIBE_API_KEY}" ]] || [[ "${VIBE_API_KEY}" == "your-api-key-here" ]]; then
        log_error "API key not configured in .env.mistrallvibe"
        log_info "Get your API key from: https://console.mistral.ai/api-keys/"
        return 1
    fi

    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js is not installed"
        return 1
    fi

    if [[ ! -f "${SERVER_SCRIPT}" ]]; then
        log_error "vibe-server.js not found"
        return 1
    fi

    log_info "Starting server on ${VIBE_HOST}:${VIBE_PORT}"
    log_info "Open http://${VIBE_HOST}:${VIBE_PORT} in your browser"
    echo ""

    export VIBE_API_KEY
    export VIBE_PORT
    export VIBE_HOST

    cd "${ROOT_DIR}"
    exec node "${SERVER_PROCESS_PATTERN}"
}

# Function: Stop Vibe
stop_vibe() {
    log_info "Stopping Mistral Vibe..."

    if pgrep -f "${SERVER_PROCESS_PATTERN}" > /dev/null 2>&1; then
        pkill -f "${SERVER_PROCESS_PATTERN}" || true
        log_success "Vibe stopped"
    else
        log_warn "Vibe process not found"
    fi
    return 0
}

# Function: Check status
status_vibe() {
    log_info "Checking Mistral Vibe status..."

    if pgrep -f "${SERVER_PROCESS_PATTERN}" > /dev/null 2>&1; then
        log_success "Vibe is RUNNING"
        log_info "Web UI: http://${VIBE_HOST}:${VIBE_PORT}"
    else
        log_warn "Vibe is NOT running"
        log_info "Start with: python -m scripts.ai vibe"
    fi
    return 0
}

# Function: Show logs
show_logs() {
    log_info "Following Vibe logs (Ctrl+C to exit)..."

    if pgrep -f "${SERVER_PROCESS_PATTERN}" > /dev/null 2>&1; then
        tail -f /tmp/vibe.log 2>/dev/null || log_warn "No logs available yet"
    else
        log_warn "Vibe is not running"
    fi
    return 0
}

# Function: Show API key
show_api_key() {
    log_info "Your Mistral Vibe API key:"

    if [[ -z "${VIBE_API_KEY}" ]] || [[ "${VIBE_API_KEY}" == "your-api-key-here" ]]; then
        log_error "API key not configured"
        log_info "1. Get key from: https://console.mistral.ai/api-keys/"
        log_info "2. Edit .env.mistrallvibe and set MISTRAL_API_KEY"
    else
        echo "  ${VIBE_API_KEY:0:10}...${VIBE_API_KEY: -10}"
        log_info "Full key shown in .env.mistrallvibe"
    fi
    return 0
}

# Function: Open browser
open_browser() {
    log_info "Opening browser..."

    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://${VIBE_HOST}:${VIBE_PORT}" &
    elif command -v open >/dev/null 2>&1; then
        open "http://${VIBE_HOST}:${VIBE_PORT}"
    else
        log_info "Open http://${VIBE_HOST}:${VIBE_PORT} in your browser"
    fi
    return 0
}

# Main dispatcher
COMMAND="${1:-start}"
shift || true

case "$COMMAND" in
    start)
        start_vibe
        ;;

    stop)
        stop_vibe
        ;;

    status)
        status_vibe
        ;;

    logs)
        show_logs
        ;;

    api-key)
        show_api_key
        ;;

    browser)
        open_browser
        ;;

    *)
        log_error "Unknown operation: $COMMAND"
        exit 1
        ;;
esac

exit $?
