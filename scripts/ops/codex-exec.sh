#!/usr/bin/env bash
# Enhanced Codex Auto-Execution Launcher for WSL
# Runs with full-auto mode (no confirmations) and improved error handling
# Usage: ./codex-exec.sh [options] "prompt"

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

if [[ $# -eq 0 ]]; then
    cat <<EOF
Codex Auto-Execution Launcher for WSL

Usage: codex-exec.sh [options] "prompt"

Options:
  --update         Update Codex to latest version
  --verbose, -v    Show detailed output
  --help, -h       Show this help message

Examples:
  # Auto-execute a refactoring task
  ./codex-exec.sh "refactor ChemBL parser for performance"

  # Update and auto-execute
  ./codex-exec.sh --update "optimize database queries"

  # Interactive execution (with confirmations)
  ./codex.sh "your prompt"
EOF
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/script-codex/helper/ensure-codex-cli.sh"

# Check for critical dependencies
if [[ ! -f "${ENSURE_SCRIPT}" ]]; then
    log_error "Codex bootstrap helper not found: ${ENSURE_SCRIPT}"
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    log_error "Node.js not found in PATH"
    log_info "Install with: sudo apt-get install nodejs npm"
    log_info "Or run setup: bash ${REPO_ROOT}/script-codex/helper/setup-wsl-complete.sh"
    exit 1
fi

# Parse flags
UPDATE_FLAG=""
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --update)
            UPDATE_FLAG="--update"
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Codex Auto-Execution Launcher for WSL

Usage: codex-exec.sh [options] "prompt"

Options:
  --update         Update Codex to latest version
  --verbose, -v    Show detailed output
  --help, -h       Show this help message

Examples:
  ./codex-exec.sh "refactor ChemBL parser for performance"
  ./codex-exec.sh --update "optimize database queries"
EOF
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

if [[ $# -eq 0 ]]; then
    log_error "No prompt provided"
    exit 1
fi

# Ensure Codex is installed
if [[ ! -x "$(${ENSURE_SCRIPT} --print-bin)" ]]; then
    log_info "Codex not found, installing..."
    if ! "${ENSURE_SCRIPT}" ${UPDATE_FLAG:+$UPDATE_FLAG}; then
        log_error "Failed to install Codex"
        exit 1
    fi
fi

# Get Codex paths
CODEX_BIN="$("${ENSURE_SCRIPT}" ${UPDATE_FLAG:+$UPDATE_FLAG} --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

if [[ ! -x "${CODEX_BIN}" ]]; then
    log_error "Codex binary not executable: ${CODEX_BIN}"
    exit 1
fi

# Set npm environment
export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

# Load WSL proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

log_success "Codex $(${CODEX_BIN} --version 2>/dev/null || echo 'unknown')"
log_success "Repository: ${REPO_ROOT}"
log_info "Prompt: $*"
log_info "Mode: Auto-execution (full-auto, no confirmations)"
echo ""

# Launch in full-auto mode
exec "${CODEX_BIN}" exec --full-auto -C "${REPO_ROOT}" "$@"
