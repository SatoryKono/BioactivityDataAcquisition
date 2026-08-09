#!/usr/bin/env bash
# DEPRECATED: This is a compatibility facade for the canonical Codex launcher.
# Please use: bash scripts/ai/codex/run-codex.sh
# This wrapper will be removed in a future release.

set -euo pipefail

# Color for deprecation warning
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[DEPRECATION WARNING]${NC} This launcher is deprecated."
echo -e "${YELLOW}[DEPRECATION WARNING]${NC} Please use: bash scripts/ai/codex/run-codex.sh"
echo -e "${YELLOW}[DEPRECATION WARNING]${NC} Redirecting to canonical launcher..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
CANONICAL_LAUNCHER="${REPO_ROOT}/scripts/ai/codex/run-codex.sh"

if [[ ! -f "${CANONICAL_LAUNCHER}" ]]; then
    echo "[codex] ERROR: Canonical launcher not found: ${CANONICAL_LAUNCHER}" >&2
    exit 1
fi

# Redirect to canonical launcher with all arguments
exec bash "${CANONICAL_LAUNCHER}" "$@"
