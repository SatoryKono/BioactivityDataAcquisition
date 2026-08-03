#!/bin/bash
# Compatibility wrapper for the legacy root Docker setup launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$SCRIPT_DIR/ops/docker-setup.sh"

if [[ ! -f "$TARGET" ]]; then
    echo "Missing canonical Docker setup script: $TARGET" >&2
    exit 1
fi

exec "$TARGET" "$@"
