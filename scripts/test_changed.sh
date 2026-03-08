#!/usr/bin/env bash
# Compatibility wrapper for canonical changed-tests runner.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$REPO_ROOT/../src/tools/scripts/test_changed.sh" "$@"
