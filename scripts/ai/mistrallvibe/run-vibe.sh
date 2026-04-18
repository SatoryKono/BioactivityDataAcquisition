#!/usr/bin/env bash
# Launch Mistral Vibe in the current repository.
# Usage: ./run-vibe.sh [args...]
#
# Examples:
#   ./run-vibe.sh                          # Interactive mode
#   ./run-vibe.sh "explain this code"      # Send prompt
#   ./run-vibe.sh --help                   # Show vibe help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_error() {
    local message="${1:-}"
    echo -e "${RED}[vibe]${NC} ERROR: ${message}" >&2
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[vibe]${NC} ${message}"
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[vibe]${NC} ${message}"
    return 0
}

# Ensure user tools are in PATH
export PATH="${HOME}/.local/bin:${PATH}"

# Source uv environment if available
if [[ -f "${HOME}/.local/bin/env" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/.local/bin/env" 2>/dev/null || true
fi

# Check if vibe is installed
if ! command -v vibe >/dev/null 2>&1; then
    log_error "Mistral Vibe CLI not found in PATH"
    echo "[vibe] Install with one of:"
    echo "[vibe]   curl -LsSf https://mistral.ai/vibe/install.sh | bash"
    echo "[vibe]   python3 -m pip install --user mistral-vibe"
    echo "[vibe]   pipx install mistral-vibe"
    echo "[vibe]"
    echo "[vibe] Or run setup: bash run-mistrallvibe.sh setup"
    exit 1
fi

# Show version
VIBE_VERSION=$(vibe --version 2>/dev/null || echo "unknown")
log_info "Using Vibe ${VIBE_VERSION}"
log_info "Working directory: ${REPO_ROOT}"

# Launch vibe
if [[ $# -eq 0 ]]; then
    log_info "Starting interactive mode..."
    exec vibe --workdir "${REPO_ROOT}"
else
    log_info "Prompt: $*"
    exec vibe --workdir "${REPO_ROOT}" "$@"
fi
