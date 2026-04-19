#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

DEFAULT_ARGS=(--config-file pyproject.toml --strict src/bioetl)
ARGS=("$@")
MYPY_NARROW="${BIOETL_MYPY_NARROW:-0}"
FILTERED_ARGS=()

for arg in "${ARGS[@]}"; do
    if [[ "$arg" == "--narrow" ]]; then
        MYPY_NARROW=1
        continue
    fi
    FILTERED_ARGS+=("$arg")
done

ARGS=("${FILTERED_ARGS[@]}")

if [[ ${#ARGS[@]} -eq 0 ]]; then
    ARGS=("${DEFAULT_ARGS[@]}")
fi

if [[ "$MYPY_NARROW" == "1" ]]; then
    ARGS=(--follow-imports=skip "${ARGS[@]}")
fi

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export BIOETL_WSL_VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"

if [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]]; then
    exec "$BIOETL_WSL_VENV_DIR/bin/python" -m mypy "${ARGS[@]}"
fi

if [[ -x ".venv/bin/python" ]]; then
    exec .venv/bin/python -m mypy "${ARGS[@]}"
fi

if [[ -d ".venv-win" ]]; then
    echo "[run_mypy][hint] A Windows virtualenv was detected. WSL should use an external venv."
    echo "[run_mypy][hint] Bootstrap it with: bash scripts/engineering/dev/setup_env_wsl.sh"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m mypy "${ARGS[@]}"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m mypy "${ARGS[@]}"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m mypy "${ARGS[@]}"
fi

echo "[run_mypy][error] Python runtime is not available." >&2
echo "[run_mypy][hint] Install dependencies first:" >&2
echo "  bash scripts/engineering/dev/setup_env_wsl.sh" >&2
exit 1
