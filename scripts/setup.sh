#!/usr/bin/env bash
# setup.sh - Compatibility wrapper for environment setup.
# Deprecated: use dev_setup.sh instead.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[setup][warn] Deprecated wrapper. Use dev_setup.sh instead."
exec bash "$REPO_ROOT/dev_setup.sh" "$@"
