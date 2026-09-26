#!/usr/bin/env bash
# Compatibility wrapper for canonical diagram checks runner.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$REPO_ROOT_GIT"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../../.." && pwd)"
fi

exec bash "$REPO_ROOT/scripts/diagrams/run_diagram_checks.sh" "$@"
