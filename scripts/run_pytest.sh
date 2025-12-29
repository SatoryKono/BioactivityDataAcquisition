#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    uv sync --extra dev --extra tests --extra tracing
else
    REQUIRED_MODULES=(pytest_asyncio pytest_cov)

    if ! uv run python - "${REQUIRED_MODULES[@]}" <<'PY'; then
        import importlib.util
        import sys

        missing = [name for name in sys.argv[1:] if importlib.util.find_spec(name) is None]
        if missing:
            print("Missing pytest plugins:", ", ".join(missing))
            raise SystemExit(1)
PY
        echo "Detected missing pytest plugins. Syncing dev/test extras..."
        uv sync --extra dev --extra tests --extra tracing
    fi
fi

PYTHONPATH="src:${PYTHONPATH:-}"
export PYTHONPATH

exec uv run pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 "$@"
