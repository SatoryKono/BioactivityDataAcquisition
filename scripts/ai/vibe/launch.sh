#!/usr/bin/env bash
# Canonical Vibe launcher for WSL/Linux with timeout protection

set -euo pipefail

print_help() {
    cat <<'EOF'
Mistral Vibe Launcher

Usage: launch.sh [args...]

Examples:
  bash scripts/ai/vibe/launch.sh
  bash scripts/ai/vibe/launch.sh "explain this code"
  bash scripts/ai/vibe/launch.sh --help
EOF
    return 0
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    print_help
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
VIBE_ENV_FILE="${REPO_ROOT}/scripts/ai/vibe/.env.vibe"

RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_error() {
    local message="${1:-}"
    echo -e "${RED}[mistral]${NC} ERROR: ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[mistral]${NC} ${message}"
    return 0
}

# Add timeout protection to PATH operations
export PATH="${HOME}/.local/bin:${PATH}"

# Load local environment with timeout protection
if timeout 5 test -f "${HOME}/.local/bin/env" 2>/dev/null \
    && timeout 5 bash -c "source '${HOME}/.local/bin/env'" 2>/dev/null; then
    # shellcheck disable=SC1091
    source "${HOME}/.local/bin/env" 2>/dev/null || true
fi

# Load shared WSL proxy environment if available with timeout
SHARED_WSL_PROXY_ENV="${REPO_ROOT}/scripts/engineering/dev/bash/.wsl_proxy_env.sh"
if timeout 5 test -f "${SHARED_WSL_PROXY_ENV}" 2>/dev/null \
    && timeout 5 bash -c "source '${SHARED_WSL_PROXY_ENV}'" 2>/dev/null; then
    # shellcheck disable=SC1090
    source "${SHARED_WSL_PROXY_ENV}" 2>/dev/null || true
fi

# Load local Vibe configuration with timeout protection
if timeout 5 test -f "${VIBE_ENV_FILE}" 2>/dev/null; then
    set -a
    # shellcheck disable=SC1090
    if timeout 5 bash -c "source '${VIBE_ENV_FILE}'" 2>/dev/null; then
        source "${VIBE_ENV_FILE}" 2>/dev/null || true
    fi
    set +a
fi

# Handle legacy API key name
if [[ -n "${VIBE_API_KEY:-}" && -z "${MISTRAL_API_KEY:-}" ]]; then
    export MISTRAL_API_KEY="${VIBE_API_KEY}"
fi

# Check if vibe is installed with timeout
if ! timeout 10 bash -c "command -v vibe >/dev/null 2>&1"; then
    log_error "Mistral Vibe CLI not found in PATH"
    echo "[mistral] Install with one of:"
    echo "[mistral]   pipx install mistral-vibe"
    echo "[mistral]   python3 -m pip install --user mistral-vibe"
    exit 1
fi

# Get Vibe version with timeout
VIBE_VERSION=$(timeout 5 vibe --version 2>/dev/null || echo "unknown")
log_info "Using Vibe ${VIBE_VERSION}"
log_info "Working directory: ${REPO_ROOT}"

if [[ -n "${MISTRAL_API_KEY:-}" ]]; then
    log_info "MISTRAL_API_KEY loaded for current session"
fi

# Launch Vibe with proper working directory
if [[ $# -eq 0 ]]; then
    log_info "Starting interactive mode..."
    exec vibe --workdir "${REPO_ROOT}"
fi

prompt_text="$*"
log_info "Prompt length: ${#prompt_text} chars"
exec vibe --workdir "${REPO_ROOT}" "$@"
