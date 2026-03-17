#!/usr/bin/env bash
# Compatibility wrapper: delegates to canonical implementation in scripts/dev/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/dev/run_pytest.sh" "$@"
