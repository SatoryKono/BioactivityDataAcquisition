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
PYTEST_PLUGIN_ARGS=()
PYTEST_NARROW="${BIOETL_PYTEST_NARROW:-0}"
FILTERED_PYTEST_ARGS=()

for arg in "${PYTEST_ARGS[@]}"; do
    if [[ "$arg" == "--narrow" ]]; then
        PYTEST_NARROW=1
        continue
    fi
    FILTERED_PYTEST_ARGS+=("$arg")
done

PYTEST_ARGS=("${FILTERED_PYTEST_ARGS[@]}")

_should_enable_benchmark_plugin() {
    local previous=""
    local arg
    for arg in "$@"; do
        case "$arg" in
            tests/benchmarks|tests/benchmarks/*|*/tests/benchmarks/*)
                return 0
                ;;
            --benchmark-only|--benchmark-compare)
                return 0
                ;;
        esac

        if [[ "$previous" == "-m" && "$arg" == *benchmark* ]]; then
            return 0
        fi
        previous="$arg"
    done
    return 1
}

if [[ "$PYTEST_NARROW" == "1" ]]; then
    export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
    DEFAULT_FLAGS=(-q --maxfail=1)
    _narrow_pytest_plugins=(
        anyio.pytest_plugin
        pytest_asyncio.plugin
        _hypothesis_pytestplugin
        pytest_timeout
        syrupy
        pytest_vcr
    )
    for plugin in "${_narrow_pytest_plugins[@]}"; do
        PYTEST_PLUGIN_ARGS+=(-p "$plugin")
    done
    if _should_enable_benchmark_plugin "${PYTEST_ARGS[@]}"; then
        PYTEST_PLUGIN_ARGS+=(-p pytest_benchmark.plugin)
    fi
elif [[ "${BIOETL_PYTEST_AUTOLOAD:-0}" != "1" ]]; then
    # The mixed Windows+WSL checkout can make third-party pytest entrypoint
    # autoload extremely slow. Keep the standard run deterministic by loading
    # only the plugins the repository relies on by default.
    export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
    _core_pytest_plugins=(
        pytest_asyncio.plugin
        pytest_timeout
        pytest_cov.plugin
        xdist.plugin
        syrupy
        pytest_vcr
        _hypothesis_pytestplugin
    )
    for plugin in "${_core_pytest_plugins[@]}"; do
        PYTEST_PLUGIN_ARGS+=(-p "$plugin")
    done
    if _should_enable_benchmark_plugin "${PYTEST_ARGS[@]}"; then
        PYTEST_PLUGIN_ARGS+=(-p pytest_benchmark.plugin)
    fi
fi

for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        --help|-h|--version|-V)
            DEFAULT_FLAGS=()
            break
            ;;
        --collect-only|--co)
            if [[ "$PYTEST_NARROW" == "1" ]]; then
                DEFAULT_FLAGS=(-q --maxfail=1)
            fi
            ;;
    esac
done

if [[ -f "scripts/ops/setup_plugins.sh" ]]; then
    bash scripts/ops/setup_plugins.sh --pytest-only
fi

if [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]]; then
    exec "$BIOETL_WSL_VENV_DIR/bin/python" -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -x ".venv/bin/python" ]]; then
    exec .venv/bin/python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -d ".venv-win" ]]; then
    echo "[run_pytest][hint] A Windows virtualenv was detected. WSL should use an external venv."
    echo "[run_pytest][hint] Bootstrap it with: bash scripts/dev/setup_env_wsl.sh"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

echo "[run_pytest][error] Python runtime is not available."
echo "[run_pytest][hint] Install dependencies first:"
echo "  bash scripts/dev/setup_env_wsl.sh"
exit 1
