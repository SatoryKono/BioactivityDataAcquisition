#!/usr/bin/env bash
# Purpose: canonical entrypoint for changed-file test selection.
# Inputs: optional base branch name (default handled by legacy runner).
# Outputs: runs pytest subsets and exits with runner status.
# Caller: Makefile test-changed target and local CLI users.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "$REPO_ROOT/src/tools/scripts/test_changed.sh" "$@"
