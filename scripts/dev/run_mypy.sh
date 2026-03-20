#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

DEFAULT_ARGS=(--config-file pyproject.toml --strict src/bioetl)
ARGS=("$@")

if [[ ${#ARGS[@]} -eq 0 ]]; then
    ARGS=("${DEFAULT_ARGS[@]}")
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m mypy "${ARGS[@]}"
fi

if [[ -x ".venv/bin/python" ]]; then
    exec .venv/bin/python -m mypy "${ARGS[@]}"
fi

if [[ -x ".venv/Scripts/python.exe" ]]; then
    exec .venv/Scripts/python.exe -m mypy "${ARGS[@]}"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m mypy "${ARGS[@]}"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m mypy "${ARGS[@]}"
fi

echo "[run_mypy][error] Python runtime is not available."
echo "[run_mypy][hint] Install dependencies first:"
echo "  uv sync --extra dev --extra tracing"
exit 1
