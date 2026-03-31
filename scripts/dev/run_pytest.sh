#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export BIOETL_WSL_VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"

DEFAULT_FLAGS=(--cov=src/bioetl --cov-report=term -q --maxfail=1)
PYTEST_ARGS=("$@")

for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        --help|-h|--version|-V)
            DEFAULT_FLAGS=()
            break
            ;;
    esac
done

if [[ -f "scripts/ops/setup_plugins.sh" ]]; then
    bash scripts/ops/setup_plugins.sh --pytest-only
fi

if [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]]; then
    exec "$BIOETL_WSL_VENV_DIR/bin/python" -m pytest "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -x ".venv/bin/python" ]]; then
    exec .venv/bin/python -m pytest "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -d ".venv-win" ]]; then
    echo "[run_pytest][hint] A Windows virtualenv was detected. WSL should use an external venv."
    echo "[run_pytest][hint] Bootstrap it with: bash scripts/dev/setup_env_wsl.sh"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m pytest "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m pytest "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m pytest "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

echo "[run_pytest][error] Python runtime is not available."
echo "[run_pytest][hint] Install dependencies first:"
echo "  bash scripts/dev/setup_env_wsl.sh"
exit 1
