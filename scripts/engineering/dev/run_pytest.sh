#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if command -v cygpath >/dev/null 2>&1 && [[ "$SCRIPT_PATH" =~ ^[A-Za-z]:\\ ]]; then
    SCRIPT_PATH="$(cygpath -u "$SCRIPT_PATH")"
fi
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export BIOETL_WSL_VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/bioetl-pycache}"
case ":${PYTHONPATH:-}:" in
    *":$REPO_ROOT/src:"*)
        ;;
    *)
        export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
        ;;
esac
PYTEST_RUNTIME_ENV_FILE="$REPO_ROOT/.pytest_cache/setup_plugins_runtime.sh"

DEFAULT_FLAGS=(-q --maxfail=1)
DEFAULT_IGNORES=(--ignore=.cache --ignore=.pytest_cache --ignore=.hypothesis)
PYTEST_ARGS=("$@")
PYTEST_PLUGIN_ARGS=()
PYTEST_NARROW="${BIOETL_PYTEST_NARROW:-0}"
PYTEST_WITH_COVERAGE="${BIOETL_PYTEST_WITH_COVERAGE:-0}"
PYTEST_NO_COV="${BIOETL_PYTEST_NO_COV:-0}"
FILTERED_PYTEST_ARGS=()
SKIP_PREFLIGHT="${BIOETL_SKIP_PREFLIGHT:-0}"
PREFLIGHT_SCOPE="${BIOETL_PREFLIGHT_SCOPE:-}"

for arg in "${PYTEST_ARGS[@]}"; do
    if [[ "$arg" == "--narrow" ]]; then
        PYTEST_NARROW=1
        continue
    fi
    if [[ "$arg" == "--with-coverage" ]]; then
        PYTEST_WITH_COVERAGE=1
        continue
    fi
    if [[ "$arg" == "--no-cov" ]]; then
        PYTEST_NO_COV=1
        continue
    fi
    if [[ "$arg" == "--skip-preflight" ]]; then
        SKIP_PREFLIGHT=1
        continue
    fi
    FILTERED_PYTEST_ARGS+=("$arg")
done

if [[ "$PYTEST_WITH_COVERAGE" == "1" && "$PYTEST_NO_COV" != "1" && "${#DEFAULT_FLAGS[@]}" -gt 0 ]]; then
    DEFAULT_FLAGS=(--cov=src/bioetl --cov-report=term "${DEFAULT_FLAGS[@]}")
fi

for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        --ignore=.cache|--ignore=.pytest_cache|--ignore=.hypothesis)
            DEFAULT_IGNORES=("${DEFAULT_IGNORES[@]/$arg}")
            ;;
        *)
            ;;
    esac
done

PYTEST_ARGS=("${FILTERED_PYTEST_ARGS[@]}")
if [[ "$PYTEST_NO_COV" == "1" ]]; then
    _filtered_no_cov_args=()
    _skip_cov_value=0
    for arg in "${PYTEST_ARGS[@]}"; do
        if [[ "$_skip_cov_value" == "1" ]]; then
            _skip_cov_value=0
            continue
        fi
        case "$arg" in
            --cov|--cov-report|--cov-config)
                _skip_cov_value=1
                continue
                ;;
            --cov=*|--cov-report=*|--cov-config=*|--no-cov)
                continue
                ;;
            *)
                _filtered_no_cov_args+=("$arg")
                ;;
        esac
    done
    PYTEST_ARGS=("${_filtered_no_cov_args[@]}")
fi

QUIET_REQUESTED=0
for arg in "${PYTEST_ARGS[@]}"; do
    case "$arg" in
        -q|--quiet|-qq|-qqq)
            QUIET_REQUESTED=1
            ;;
        *)
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
        *)
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
            *)
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
            *)
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
            *)
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
            *)
                ;;
        esac

        local candidate="${arg%%::*}"
        case "$candidate" in
            tests|tests/*)
                _SELECTED_TEST_PATHS+=("$candidate")
                ;;
            *)
                ;;
        esac
    done
    return 0
}

_has_selected_test_paths() {
    if [[ "${#_SELECTED_TEST_PATHS[@]}" -gt 0 ]]; then
        return 0
    fi
    return 1
}

_selected_has_exact_test_root() {
    local target
    for target in "${_SELECTED_TEST_PATHS[@]}"; do
        if [[ "$target" == "tests" ]]; then
            return 0
        fi
    done
    return 1
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
                *)
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
                *)
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

_needs_full_test_capabilities_for_selection() {
    if ! _has_selected_test_paths; then
        return 0
    fi

    if _selected_has_exact_test_root; then
        return 0
    fi

    _paths_match_any \
        tests/architecture \
        tests/benchmarks \
        tests/unit/application/core \
        tests/unit/composition/bootstrap/runtime \
        tests/unit/infrastructure/observability \
        tests/unit/infrastructure/serialization
}

python_has_required_test_runtime() {
    local python_bin="$1"
    local require_full_capabilities="${2:-0}"
    [[ -x "$python_bin" ]] || return 1
    BIOETL_REQUIRE_TEST_CAPABILITIES="$require_full_capabilities" "$python_bin" - <<'PY' >/dev/null 2>&1
import importlib.util
import os

required = (
    "pytest",
    "pytest_asyncio",
    "pytest_cov",
    "xdist",
    "pytest_timeout",
    "pytest_vcr",
    "syrupy",
    "_hypothesis_pytestplugin",
    "pydantic",
    "pandas",
    "httpx",
    "click",
    "structlog",
    "pandera",
    "respx",
)

if os.environ.get("BIOETL_REQUIRE_TEST_CAPABILITIES") == "1":
    required += (
        "opentelemetry.sdk",
        "orjson",
        "polars",
        "radon",
        "vulture",
        "importlinter",
        "pytest_benchmark",
    )

raise SystemExit(0 if all(importlib.util.find_spec(module) is not None for module in required) else 1)
PY
}

should_run_preflight() {
    if [[ "$SKIP_PREFLIGHT" == "1" || "${BIOETL_PREFLIGHT_DONE:-0}" == "1" || "${BIOETL_PREFLIGHT_ACTIVE:-0}" == "1" ]]; then
        return 1
    fi

    if [[ "$PYTEST_NARROW" == "1" ]]; then
        return 1
    fi

    local arg
    for arg in "${PYTEST_ARGS[@]}"; do
        case "$arg" in
            --help|-h|--version|-V|--collect-only|--co)
                return 1
                ;;
            *)
                ;;
        esac
    done

    if [[ -n "$PREFLIGHT_SCOPE" ]]; then
        return 0
    fi

    if ! _has_selected_test_paths; then
        return 0
    fi

    if _selected_has_exact_test_root; then
        return 0
    fi

    _paths_match_any tests/architecture tests/integration/config tests/integration/ci
}

determine_preflight_scope() {
    if [[ -n "$PREFLIGHT_SCOPE" ]]; then
        printf '%s\n' "$PREFLIGHT_SCOPE"
        return 0
    fi
    printf '%s\n' "full"
}

_selected_is_compatibility_inventory_guard() {
    _has_selected_test_paths || return 1
    _selected_has_exact_test_root && return 1

    local matched=0
    local target
    for target in "${_SELECTED_TEST_PATHS[@]}"; do
        case "$target" in
            tests/architecture/test_compatibility_facade_inventory.py|tests/architecture/test_compatibility_telemetry_reporting.py)
                matched=1
                ;;
            *)
                return 1
                ;;
        esac
    done

    [[ "$matched" == "1" ]]
}

determine_preflight_mode() {
    if _selected_is_compatibility_inventory_guard; then
        printf '%s\n' "check"
        return 0
    fi
    printf '%s\n' "auto"
}

if _needs_cov_plugin "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}" && [[ -z "${COVERAGE_FILE:-}" ]]; then
    mkdir -p /tmp/bioetl-coverage
    coverage_file="$(mktemp /tmp/bioetl-coverage/.coverage.XXXXXX.sqlite)"
    rm -f "$coverage_file"
    export COVERAGE_FILE="$coverage_file"
fi

_collect_selected_test_paths "${PYTEST_ARGS[@]}"
REQUIRE_FULL_TEST_CAPABILITIES=0
if _needs_full_test_capabilities_for_selection; then
    REQUIRE_FULL_TEST_CAPABILITIES=1
fi
export BIOETL_REQUIRE_TEST_CAPABILITIES="$REQUIRE_FULL_TEST_CAPABILITIES"

if should_run_preflight && [[ -f "scripts/engineering/dev/pretest_guardrails.sh" ]]; then
    preflight_scope="$(determine_preflight_scope)"
    preflight_mode="$(determine_preflight_mode)"
    preflight_cmd=(bash scripts/engineering/dev/pretest_guardrails.sh --mode "$preflight_mode" --scope "$preflight_scope")
    if [[ "${BIOETL_PREFLIGHT_STRICT_DOCS:-0}" == "1" ]]; then
        preflight_cmd+=(--strict-docs)
    fi
    BIOETL_PREFLIGHT_ACTIVE=1 "${preflight_cmd[@]}"
    export BIOETL_PREFLIGHT_DONE=1
fi

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

if [[ -f "scripts/ops/launchers/codex/setup_plugins.sh" ]]; then
    bash scripts/ops/launchers/codex/setup_plugins.sh --pytest-only
fi

if [[ -f "$PYTEST_RUNTIME_ENV_FILE" ]]; then
    # setup_plugins.sh may provision a temporary pytest runtime under /tmp when
    # the configured WSL venv is missing pytest or is not writable.
    # shellcheck disable=SC1090
    source "$PYTEST_RUNTIME_ENV_FILE"
fi

if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]]; then
    runtime_bin_dir="$(dirname "$BIOETL_PYTEST_RUNTIME_PYTHON")"
    case ":${PATH:-}:" in
        *":$runtime_bin_dir:"*)
            ;;
        *)
            export PATH="$runtime_bin_dir${PATH:+:$PATH}"
            ;;
    esac
fi

if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]] && python_has_required_test_runtime "$BIOETL_PYTEST_RUNTIME_PYTHON" "$REQUIRE_FULL_TEST_CAPABILITIES"; then
    exec "$BIOETL_PYTEST_RUNTIME_PYTHON" -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -x "$BIOETL_WSL_VENV_DIR/bin/python" ]] && python_has_required_test_runtime "$BIOETL_WSL_VENV_DIR/bin/python" "$REQUIRE_FULL_TEST_CAPABILITIES"; then
    exec "$BIOETL_WSL_VENV_DIR/bin/python" -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -x ".venv/bin/python" ]] && python_has_required_test_runtime ".venv/bin/python" "$REQUIRE_FULL_TEST_CAPABILITIES"; then
    exec .venv/bin/python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if [[ -d ".venv-win" ]]; then
    echo "[run_pytest][hint] A Windows virtualenv was detected. WSL should use an external venv."
    echo "[run_pytest][hint] Bootstrap it with: bash scripts/engineering/dev/setup_env_wsl.sh"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python >/dev/null 2>&1; then
    exec python -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 -m pytest "${PYTEST_PLUGIN_ARGS[@]}" "${DEFAULT_IGNORES[@]}" "${DEFAULT_FLAGS[@]}" "${PYTEST_ARGS[@]}"
fi

echo "[run_pytest][error] Python runtime is not available." >&2
echo "[run_pytest][hint] Install dependencies first:" >&2
echo "  bash scripts/engineering/dev/setup_env_wsl.sh"
exit 1
