#!/usr/bin/env bash
# Compatibility launcher for the canonical scripts/ai/mistrall surface.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_DIR="$(cd "${SCRIPT_DIR}/../mistrall" && pwd)"

exec bash "${CANONICAL_DIR}/run-mistrall.sh" "$@"
