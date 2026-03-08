#!/usr/bin/env bash
# Compatibility wrapper for canonical script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" pwd)"
exec bash "$REPO_ROOT/scripts/ops/close_duplicate_prs_wave3.sh" "$@"
