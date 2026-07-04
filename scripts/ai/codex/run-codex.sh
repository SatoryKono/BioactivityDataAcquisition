#!/usr/bin/env bash
# Codex - Main Entry Point (WSL)
# Usage: ./run-codex.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../..")}"
USER_NPM_BIN="${HOME}/.npm-global/bin"

# Prefer user-scoped npm globals over stale system-wide installs.
if [[ -d "${USER_NPM_BIN}" ]]; then
    export PATH="${USER_NPM_BIN}:${PATH}"
fi

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

resolve_codex_bin() {
    local candidate=""
    if [[ -n "${CODEX_BIN:-}" ]] && [[ -x "${CODEX_BIN}" ]]; then
        printf "%s\n" "${CODEX_BIN}"
        return 0
    fi
    if [[ -x "${USER_NPM_BIN}/codex" ]]; then
        printf "%s\n" "${USER_NPM_BIN}/codex"
        return 0
    fi
    candidate="$(command -v codex 2>/dev/null || true)"
    if [[ -n "${candidate}" ]]; then
        printf "%s\n" "${candidate}"
        return 0
    fi
    return 1
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
  mcp-check      Check Codex MCP configuration
  mcp-setup      Sync Codex MCP configuration
  help           Show this help

Examples:
  ./run-codex.sh
  ./run-codex.sh "analyze the code"
  ./run-codex.sh exec "refactor the parser"
  ./run-codex.sh login

EOF
    exit 0
fi

COMMAND="${1:-start}"

case "$COMMAND" in
    check)
        bash "${HELPER_DIR}/check-env.sh"
        exit $?
        ;;
    setup)
        bash "${HELPER_DIR}/setup-env.sh"
        exit $?
        ;;
    mcp-check)
        bash "${HELPER_DIR}/ensure-mcp.sh" --check
        exit $?
        ;;
    mcp-setup)
        bash "${HELPER_DIR}/ensure-mcp.sh" --ensure
        exit $?
        ;;
    *)
        ;;
esac

# Check environment (with retry limit)
log_info "Checking environment setup..."
echo ""

RETRY_COUNT=0
MAX_RETRIES=2

while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
    if bash "${HELPER_DIR}/check-env.sh" 2>/dev/null; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))

    if [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; then
        log_warn "Some components missing (attempt $RETRY_COUNT/$MAX_RETRIES)"
        log_info "Running setup to install missing components..."
        echo ""

        if ! bash "${HELPER_DIR}/setup-env.sh"; then
            log_error "Setup failed on attempt $RETRY_COUNT"
            exit 1
        fi
        echo ""
    fi
done

if [[ $RETRY_COUNT -eq $MAX_RETRIES ]]; then
    log_error "Environment check failed after $MAX_RETRIES attempts"
    exit 1
fi

echo ""
log_info "Environment ready - launching Codex"
echo ""

# Locate .env.codex without creating local secret-bearing files by default.
SCRIPT_DIR_CODEX="${SCRIPT_DIR}"
ENV_FILE="${SCRIPT_DIR_CODEX}/.env.codex"
if [[ ! -f "${ENV_FILE}" ]]; then
    log_warn ".env.codex not found, checking repo root..."
    # Try repo root as fallback
    ENV_FILE="${REPO_ROOT}/.env.codex"
    if [[ ! -f "${ENV_FILE}" ]]; then
        if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" != "1" ]]; then
            log_error ".env.codex not found. Create it manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to generate a local template."
            exit 1
        fi
        log_warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.codex in scripts/ai/codex/..."
        cat > "${SCRIPT_DIR_CODEX}/.env.codex" <<'ENVEOF'
# OpenAI Codex Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
ENVEOF
        log_error "Please edit ${SCRIPT_DIR_CODEX}/.env.codex and add your OpenAI API key"
        exit 1
    fi
fi

# Process command
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
        CODEX_LOGIN_BIN="$(resolve_codex_bin || true)"
        if [[ -z "${CODEX_LOGIN_BIN}" ]]; then
            log_error "Codex CLI not found in PATH"
            log_info "Run: bash ${HELPER_DIR}/setup-env.sh"
            exit 1
        fi
        "${CODEX_LOGIN_BIN}" login
        ;;

    device-login)
        CODEX_LOGIN_BIN="$(resolve_codex_bin || true)"
        if [[ -z "${CODEX_LOGIN_BIN}" ]]; then
            log_error "Codex CLI not found in PATH"
            log_info "Run: bash ${HELPER_DIR}/setup-env.sh"
            exit 1
        fi
        "${CODEX_LOGIN_BIN}" login --device-auth
        ;;

    *)
        # Treat as prompt
        bash "${HELPER_DIR}/run-codex-impl.sh" "$COMMAND" "$@"
        ;;
esac

exit $?
