#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -f "scripts/ops/setup_plugins.sh" ]]; then
    bash scripts/ops/setup_plugins.sh --pytest-only
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
fi

if [[ -x ".venv/bin/python" ]]; then
    exec .venv/bin/python -m pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
fi

echo "[run_pytest][error] Python runtime is not available."
echo "[run_pytest][hint] Install dependencies first:"
echo "  uv sync --extra dev --extra tests --extra tracing"
exit 1
