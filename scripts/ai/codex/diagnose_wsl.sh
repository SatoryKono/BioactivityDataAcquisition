#!/usr/bin/env bash
# Canonical Codex WSL diagnostics entrypoint.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_DIR="${SCRIPT_DIR}/helper"
VERBOSE=0

for arg in "$@"; do
    case "$arg" in
        --verbose)
            VERBOSE=1
            ;;
        help|-h|--help)
            cat <<'EOF'
Usage: ./diagnose_wsl.sh [--verbose]

Run the Codex WSL diagnostics.

  default    quick environment and MCP readiness check
  --verbose  include the full setup verification report
EOF
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

echo "=================================================="
echo "  Codex WSL Diagnostics"
echo "=================================================="
echo ""

set +e
bash "${HELPER_DIR}/check-env.sh"
CHECK_STATUS=$?
set -e

if [[ "${VERBOSE}" == "1" || "${CHECK_STATUS}" -ne 0 ]]; then
    echo ""
    echo "[INFO] Running extended verification..."
    echo ""
    bash "${HELPER_DIR}/verify-setup.sh"
fi

exit "${CHECK_STATUS}"
