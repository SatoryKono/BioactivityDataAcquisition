#!/usr/bin/env bash
set -euo pipefail

AGENT_TOOLS="none"
AGENTDEBUGX_EXTRA="agentdebugx"
PROOFAGENT_EXTRA="proofagent"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --agent-tools)
            if [[ $# -lt 2 ]]; then
                echo "[setup_env_wsl][error] --agent-tools requires: none, agentdebugx, proofagent, or all." >&2
                exit 2
            fi
            AGENT_TOOLS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--agent-tools none|agentdebugx|proofagent|all]"
            exit 0
            ;;
        *)
            echo "[setup_env_wsl][error] Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

case "$AGENT_TOOLS" in
    none|"$AGENTDEBUGX_EXTRA"|"$PROOFAGENT_EXTRA"|all) ;;
    *)
        echo "[setup_env_wsl][error] Invalid --agent-tools value: $AGENT_TOOLS" >&2
        exit 2
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
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
    # Lockfile-backed sync; --no-build refuses sdist/setup-script execution (shell:S8541).
    UV_NO_BUILD=1 uv sync --active --frozen --no-build --extra dev --extra tests --extra tracing || {
        echo "[setup_env_wsl][error] uv sync failed." >&2
        echo "[setup_env_wsl][hint] Retry with the same command; UV_HTTP_TIMEOUT defaults to $UV_HTTP_TIMEOUT seconds." >&2
        exit 1
    }

    OPTIONAL_EXTRAS=()
    [[ "$AGENT_TOOLS" == "$AGENTDEBUGX_EXTRA" || "$AGENT_TOOLS" == "all" ]] && OPTIONAL_EXTRAS+=("$AGENTDEBUGX_EXTRA")
    [[ "$AGENT_TOOLS" == "$PROOFAGENT_EXTRA" || "$AGENT_TOOLS" == "all" ]] && OPTIONAL_EXTRAS+=("$PROOFAGENT_EXTRA")
    INSTALLED_EXTRAS=()
    OPTIONAL_FAILURES=0
    for EXTRA in "${OPTIONAL_EXTRAS[@]}"; do
        SYNC_ARGS=(--active --frozen --no-build --extra dev --extra tests --extra tracing)
        for INSTALLED in "${INSTALLED_EXTRAS[@]}"; do
            SYNC_ARGS+=(--extra "$INSTALLED")
        done
        SYNC_ARGS+=(--extra "$EXTRA")
        if UV_NO_BUILD=1 uv sync "${SYNC_ARGS[@]}"; then
            INSTALLED_EXTRAS+=("$EXTRA")
            echo "[setup_env_wsl][ok] Optional tool installed: $EXTRA"
        else
            OPTIONAL_FAILURES=1
            echo "[setup_env_wsl][error] Optional tool failed without blocking the remaining tools: $EXTRA" >&2
        fi
    done
else
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$VENV_DIR"
    elif command -v python >/dev/null 2>&1; then
        python -m venv "$VENV_DIR"
    else
        echo "[setup_env_wsl][error] Neither uv, python3, nor python is available." >&2
        exit 1
    fi

    # Binary-only bootstrap + project extras (shell:S8541).
    "$VENV_PYTHON" -m pip install --only-binary=:all: --upgrade "pip==25.0.1" "setuptools==75.8.0" "wheel==0.45.1"
    "$VENV_PYTHON" -m pip install --only-binary=:all: -e '.[dev,tests,tracing]'
    OPTIONAL_EXTRAS=()
    [[ "$AGENT_TOOLS" == "$AGENTDEBUGX_EXTRA" || "$AGENT_TOOLS" == "all" ]] && OPTIONAL_EXTRAS+=("$AGENTDEBUGX_EXTRA")
    [[ "$AGENT_TOOLS" == "$PROOFAGENT_EXTRA" || "$AGENT_TOOLS" == "all" ]] && OPTIONAL_EXTRAS+=("$PROOFAGENT_EXTRA")
    OPTIONAL_FAILURES=0
    for EXTRA in "${OPTIONAL_EXTRAS[@]}"; do
        if "$VENV_PYTHON" -m pip install --only-binary=:all: -e ".[dev,tests,tracing,$EXTRA]"; then
            echo "[setup_env_wsl][ok] Optional tool installed: $EXTRA"
        else
            OPTIONAL_FAILURES=1
            echo "[setup_env_wsl][error] Optional tool failed without blocking the remaining tools: $EXTRA" >&2
        fi
    done
fi

echo "[setup_env_wsl][ok] Environment ready at $VENV_DIR"
echo "[setup_env_wsl][hint] Activate with: source \"$VENV_DIR/bin/activate\""
echo "[setup_env_wsl][hint] Run tests with: bash scripts/engineering/dev/run_pytest.sh tests/unit --narrow --timeout=120 --lf"
if [[ "${OPTIONAL_FAILURES:-0}" -ne 0 ]]; then
    exit 1
fi
