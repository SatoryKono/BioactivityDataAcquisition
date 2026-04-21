#!/usr/bin/env bash
# Compatibility launcher for the canonical Vibe surface.
# Usage: ./run-vibe.sh [check|setup|args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"
HELPER_DIR="${SCRIPT_DIR}/helper"
CANONICAL_LAUNCHER="${REPO_ROOT}/scripts/ai/vibe/launch.sh"

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

print_help() {
    cat <<'EOF'
Mistral Vibe Compatibility Launcher

Usage: run-vibe.sh [command|args...]

Commands:
  check    Verify local setup
  setup    Install/configure Vibe
  --help   Show this help

All other arguments are forwarded to scripts/ai/vibe/launch.sh.
EOF
    return 0
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
    check)
        exec bash "${HELPER_DIR}/check-env.sh"
        ;;
    setup)
        exec bash "${HELPER_DIR}/setup-env.sh"
        ;;
    *)
        ;;
esac

if [[ ! -x "${CANONICAL_LAUNCHER}" ]]; then
    log_error "Canonical Vibe launcher not found: ${CANONICAL_LAUNCHER}"
    exit 1
fi

exec bash "${CANONICAL_LAUNCHER}" "$@"
