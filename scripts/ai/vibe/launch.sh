#!/usr/bin/env bash
# Canonical Vibe launcher for WSL/Linux.

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

export PATH="${HOME}/.local/bin:${PATH}"

if [[ -f "${HOME}/.local/bin/env" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/.local/bin/env" 2>/dev/null || true
fi

if ! command -v vibe >/dev/null 2>&1; then
    log_error "Mistral Vibe CLI not found in PATH"
    echo "[mistral] Install with one of:"
    echo "[mistral]   curl -LsSf https://mistral.ai/vibe/install.sh | bash"
    echo "[mistral]   python3 -m pip install --user mistral-vibe"
    echo "[mistral]   pipx install mistral-vibe"
    exit 1
fi

VIBE_VERSION=$(vibe --version 2>/dev/null || echo "unknown")
log_info "Using Vibe ${VIBE_VERSION}"
log_info "Working directory: ${REPO_ROOT}"

if [[ $# -eq 0 ]]; then
    log_info "Starting interactive mode..."
    exec vibe --workdir "${REPO_ROOT}"
fi

log_info "Prompt: $*"
exec vibe --workdir "${REPO_ROOT}" "$@"
