#!/usr/bin/env bash
# Compatibility wrapper for canonical script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/ops/close_superseded_prs.sh" "$@"
