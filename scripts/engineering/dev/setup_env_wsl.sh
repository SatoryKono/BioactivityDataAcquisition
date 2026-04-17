#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$REPO_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-180}"

VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ -e "$REPO_ROOT/.venv-wsl" ]]; then
    echo "[setup_env_wsl][hint] Found a repository-local .venv-wsl. Remove it to avoid Windows conflicts."
fi

if [[ -d "$REPO_ROOT/.venv" && ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "[setup_env_wsl][hint] Found a non-WSL .venv. It will be ignored in favor of an external WSL venv."
fi

mkdir -p "$(dirname "$VENV_DIR")"

if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV_DIR" --python 3.13 --allow-existing
    export VIRTUAL_ENV="$VENV_DIR"
    export PATH="$VENV_DIR/bin:$PATH"
    uv sync --active --extra dev --extra tracing || {
        echo "[setup_env_wsl][error] uv sync failed."
        echo "[setup_env_wsl][hint] Retry with the same command; UV_HTTP_TIMEOUT defaults to $UV_HTTP_TIMEOUT seconds."
        exit 1
    }
else
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$VENV_DIR"
    elif command -v python >/dev/null 2>&1; then
        python -m venv "$VENV_DIR"
    else
        echo "[setup_env_wsl][error] Neither uv, python3, nor python is available."
        exit 1
    fi

    "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
    "$VENV_PYTHON" -m pip install -e '.[dev,tracing]'
fi

echo "[setup_env_wsl][ok] Environment ready at $VENV_DIR"
echo "[setup_env_wsl][hint] Activate with: source \"$VENV_DIR/bin/activate\""
echo "[setup_env_wsl][hint] Run tests with: bash scripts/engineering/dev/run_pytest.sh tests/unit --narrow --timeout=120 --lf"
