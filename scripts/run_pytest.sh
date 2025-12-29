#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    uv sync --extra dev --extra tracing
fi

PYTHONPATH="src:${PYTHONPATH:-}"
export PYTHONPATH

exec uv run pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
