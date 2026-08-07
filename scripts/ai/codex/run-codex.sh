#!/usr/bin/env bash
# Codex - Main Entry Point (WSL)
# Usage: ./run-codex.sh [command] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../..")}"
USER_NPM_BIN="${HOME}/.npm-global/bin"
LINUX_NPM_BIN="${HOME}/.cache/bioetl-codex/npm-global/bin"

# Prefer Linux-native and user-scoped npm globals over stale system installs.
# /usr/local/bin/codex is often root-owned and lagging behind @latest.
if [[ -d "${LINUX_NPM_BIN}" ]]; then
    export PATH="${LINUX_NPM_BIN}:${PATH}"
fi
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
    if [[ -x "${LINUX_NPM_BIN}/codex" ]]; then
        printf "%s\n" "${LINUX_NPM_BIN}/codex"
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
  mcp-check      Run bounded profile-aware MCP readiness checks
  mcp-static     Check Codex MCP configuration without live services
  mcp-setup      Force-refresh Codex MCP configuration
  baseline       Measure bounded launcher and MCP overhead
  diagnose       Run canonical WSL/Codex diagnostics
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
        python3 "${SCRIPT_DIR}/doctor.py" mcp "${@:2}"
        exit $?
        ;;
    mcp-static)
        bash "${HELPER_DIR}/ensure-mcp.sh" --check
        exit $?
        ;;
    mcp-setup)
        bash "${HELPER_DIR}/ensure-mcp.sh" --refresh
        exit $?
        ;;
    baseline)
        python3 "${SCRIPT_DIR}/efficiency_baseline.py" "${@:2}"
        exit $?
        ;;
    diagnose)
        bash "${SCRIPT_DIR}/diagnose_wsl.sh" "${@:2}"
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

# Optional .env.codex for API-key mode. ChatGPT device auth in ~/.codex/auth.json
# is enough for launch; never create secret-bearing files without an explicit opt-in.
# shellcheck source=helper/codex-auth-lib.sh
source "${HELPER_DIR}/codex-auth-lib.sh"
SCRIPT_DIR_CODEX="${SCRIPT_DIR}"
ENV_FILE="${SCRIPT_DIR_CODEX}/.env.codex"
if [[ ! -f "${ENV_FILE}" ]]; then
    ENV_FILE="${REPO_ROOT}/.env.codex"
fi
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi
if ! codex_has_usable_auth; then
    if [[ ! -f "${SCRIPT_DIR_CODEX}/.env.codex" && ! -f "${REPO_ROOT}/.env.codex" ]]; then
        if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" == "1" ]]; then
            log_warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.codex template in scripts/ai/codex/..."
            cat > "${SCRIPT_DIR_CODEX}/.env.codex" <<'ENVEOF'
# OpenAI Codex Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
ENVEOF
            log_error "Edit ${SCRIPT_DIR_CODEX}/.env.codex and add your OpenAI API key, or run: bash scripts/ai/codex/run-codex.sh device-login"
            exit 1
        fi
        log_error "No Codex auth found (no ChatGPT session and no .env.codex API key)."
        log_info "Recommended under WSL: bash scripts/ai/codex/run-codex.sh device-login"
        log_info "Or create scripts/ai/codex/.env.codex with OPENAI_API_KEY (opt-in template: BIOETL_CREATE_LOCAL_ENV_FILES=1)."
        exit 1
    fi
    log_error "Auth files present but unusable. Run device-login or fix OPENAI_API_KEY."
    exit 1
fi
log_info "Auth ready: $(codex_auth_status_label)"

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
