#!/usr/bin/env bash
# Compatibility wrapper for canonical script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" pwd)"
exec bash "$REPO_ROOT/scripts/docs/build_docs_site.sh" "$@"
