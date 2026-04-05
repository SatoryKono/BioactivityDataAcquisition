#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export BIOETL_WSL_VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/bioetl-pycache}"

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

QUIET_REQUESTED=0
for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        -q|--quiet|-qq|-qqq)
            QUIET_REQUESTED=1
            ;;
    esac
done

for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        --help|-h|--version|-V)
            DEFAULT_FLAGS=()
            break
            ;;
        --collect-only|--co)
            DEFAULT_FLAGS=(-q --maxfail=1)
            ;;
    esac
done

if [[ "${BIOETL_PYTEST_LIVE_OUTPUT:-0}" == "1" && "$QUIET_REQUESTED" != "1" ]]; then
    if [[ "${DEFAULT_FLAGS[*]}" == *" -q "* || "${DEFAULT_FLAGS[*]}" == "-q "* || "${DEFAULT_FLAGS[*]}" == *" -q" ]]; then
        DEFAULT_FLAGS=("${DEFAULT_FLAGS[@]/-q}")
    fi
    DEFAULT_FLAGS+=(-o console_output_style=progress)
fi

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

_needs_cov_plugin() {
    local arg
    for arg in "$@"; do
        case "$arg" in
            --cov|--cov=*|--cov-report|--cov-report=*|--cov-config|--cov-config=*)
                return 0
                ;;
        esac
    done
    return 1
}

_needs_xdist_plugin() {
    local previous=""
    local arg
    for arg in "$@"; do
        case "$arg" in
            -n|--numprocesses|--dist|--dist=*|--tx|--tx=*)
                return 0
                ;;
            -n*)
                [[ "$arg" != "-q" ]] && return 0
                ;;
        esac
        if [[ "$previous" == "-p" && "$arg" == "xdist.plugin" ]]; then
            return 0
        fi
        previous="$arg"
    done
    return 1
}

_SELECTED_TEST_PATHS=()

_collect_selected_test_paths() {
    _SELECTED_TEST_PATHS=()
    local expects_value=0
    local arg
    for arg in "$@"; do
        if [[ "$expects_value" == "1" ]]; then
            expects_value=0
            continue
        fi

        case "$arg" in
            -k|-m|-n|-o|-p|--maxfail|--timeout|--durations|--durations-min|--dist|--cov|--cov-report|--cov-config|--rootdir|--basetemp|--ignore|--ignore-glob)
                expects_value=1
                continue
                ;;
            --dist=*|--cov=*|--cov-report=*|--cov-config=*|--rootdir=*|--basetemp=*|--timeout=*|--maxfail=*|--durations=*|--durations-min=*|--ignore=*|--ignore-glob=*)
                continue
                ;;
            -n*)
                [[ "$arg" != "-q" ]] && continue
                ;;
            -*)
                continue
                ;;
        esac

        local candidate="${arg%%::*}"
        case "$candidate" in
            tests|tests/*)
                _SELECTED_TEST_PATHS+=("$candidate")
                ;;
        esac
    done
}

_has_selected_test_paths() {
    [[ "${#_SELECTED_TEST_PATHS[@]}" -gt 0 ]]
}

_paths_match_any() {
    local target
    local prefix
    for target in "${_SELECTED_TEST_PATHS[@]}"; do
        for prefix in "$@"; do
            case "$target" in
                "$prefix"|"$prefix"/*)
                    return 0
                    ;;
            esac
        done
    done
    return 1
}

_selected_dirs_match_any() {
    local target
    local prefix
    for target in "${_SELECTED_TEST_PATHS[@]}"; do
        [[ -d "$target" ]] || continue
        for prefix in "$@"; do
            case "$target" in
                "$prefix"|"$prefix"/*)
                    return 0
                    ;;
            esac
        done
    done
    return 1
}

_needs_vcr_plugin() {
    if ! _has_selected_test_paths; then
        return 0
    fi
    _paths_match_any tests/integration tests/e2e tests/contract
}

_needs_syrupy_plugin() {
    if ! _has_selected_test_paths; then
        return 0
    fi

    if _selected_dirs_match_any tests/unit; then
        return 0
    fi

    _paths_match_any \
        tests/unit/application/pipelines/test_transformer_snapshots.py \
        tests/unit/interfaces/cli/test_registry_consistency.py
}

_needs_hypothesis_plugin_for_selection() {
    if ! _has_selected_test_paths; then
        return 0
    fi

    if _selected_dirs_match_any tests/unit tests/architecture; then
        return 0
    fi

    _paths_match_any \
        tests/unit/domain/test_exceptions.py \
        tests/unit/domain/test_transformations.py \
        tests/unit/domain/services/test_identity_service.py \
        tests/unit/infrastructure/validation/test_pandera_validator.py \
        tests/architecture/test_port_contracts_hypothesis.py
}

if _needs_cov_plugin "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}" && [[ -z "${COVERAGE_FILE:-}" ]]; then
    mkdir -p /tmp/bioetl-coverage
    export COVERAGE_FILE="/tmp/bioetl-coverage/.coverage.$$.sqlite"
fi

_collect_selected_test_paths "${PYTEST_ARGS[@]}"

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
    )
    if _needs_syrupy_plugin; then
        _core_pytest_plugins+=(syrupy)
    fi
    if _needs_vcr_plugin; then
        _core_pytest_plugins+=(pytest_vcr)
    fi
    if _needs_hypothesis_plugin_for_selection; then
        _core_pytest_plugins+=(_hypothesis_pytestplugin)
    fi
    if _needs_cov_plugin "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"; then
        _core_pytest_plugins+=(pytest_cov.plugin)
    fi
    if _needs_xdist_plugin "${PYTEST_ARGS[@]}"; then
        _core_pytest_plugins+=(xdist.plugin)
    fi
    for plugin in "${_core_pytest_plugins[@]}"; do
        PYTEST_PLUGIN_ARGS+=(-p "$plugin")
    done
    if _should_enable_benchmark_plugin "${PYTEST_ARGS[@]}"; then
        PYTEST_PLUGIN_ARGS+=(-p pytest_benchmark.plugin)
    fi
fi

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
