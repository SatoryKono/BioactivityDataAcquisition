#!/usr/bin/env bash
# Compatibility wrapper for canonical script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../../.." && pwd)"
exec bash "$REPO_ROOT/scripts/diagrams/run_diagram_docs_agent.sh" "$@"
