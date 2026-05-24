#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if command -v cygpath >/dev/null 2>&1 && [[ "$SCRIPT_PATH" =~ ^[A-Za-z]:\\ ]]; then
    SCRIPT_PATH="$(cygpath -u "$SCRIPT_PATH")"
fi
if command -v readlink >/dev/null 2>&1; then
    RESOLVED_SCRIPT_PATH="$(readlink -f "$SCRIPT_PATH" 2>/dev/null || true)"
    if [[ -n "$RESOLVED_SCRIPT_PATH" ]]; then
        SCRIPT_PATH="$RESOLVED_SCRIPT_PATH"
    fi
fi
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

RUNNER="$SCRIPT_DIR/run_pytest.sh"
INVENTORY_PATH="$REPO_ROOT/configs/quality/pytest_shards.yaml"
DEFAULT_WORKERS_PER_SHARD=2
DEFAULT_DIST_MODE="loadfile"
DEFAULT_COVERAGE_DIR="$REPO_ROOT/.coverage-sharded"
DEFAULT_COVERAGE_REPORT_DIR="$REPO_ROOT/reports/coverage"
DEFAULT_PYTEST_CACHE_DIR="$REPO_ROOT/.pytest_cache"
if [[ -n "${BIOETL_JUNIT_RUN_ID:-}" ]]; then
    DEFAULT_JUNIT_DIR="$REPO_ROOT/reports/quality/test-runs/junit/$BIOETL_JUNIT_RUN_ID"
else
    DEFAULT_JUNIT_DIR="$REPO_ROOT/reports/quality/test-runs/junit/run-$(date +%Y%m%dT%H%M%S)"
fi
DEFAULT_TEST_HEALTH_REPORTS_DIR="$REPO_ROOT/reports/quality/test-runs"

WORKERS_PER_SHARD="$DEFAULT_WORKERS_PER_SHARD"
DIST_MODE="$DEFAULT_DIST_MODE"
COVERAGE_DIR="$DEFAULT_COVERAGE_DIR"
COVERAGE_REPORT_DIR="${BIOETL_PYTEST_SHARDED_COVERAGE_REPORT_DIR:-$DEFAULT_COVERAGE_REPORT_DIR}"
PYTEST_CACHE_DIR="$DEFAULT_PYTEST_CACHE_DIR"
JUNIT_DIR="$DEFAULT_JUNIT_DIR"
TEST_HEALTH_SUITE="${BIOETL_PYTEST_SHARDED_TEST_HEALTH_SUITE:-coverage-verify}"
TEST_HEALTH_REPORTS_DIR="${BIOETL_PYTEST_SHARDED_TEST_HEALTH_REPORTS_DIR:-$DEFAULT_TEST_HEALTH_REPORTS_DIR}"
TEST_HEALTH_ROLLUP_MD="${BIOETL_PYTEST_SHARDED_TEST_HEALTH_ROLLUP_MD:-$TEST_HEALTH_REPORTS_DIR/rollup.md}"
TEST_HEALTH_TIMEOUT_SECONDS="${BIOETL_PYTEST_SHARDED_TEST_HEALTH_TIMEOUT_SECONDS:-60}"
FORCE_MOUNTED_COVERAGE="${BIOETL_PYTEST_SHARDED_FORCE_COVERAGE:-0}"
STREAM_LOGS=0
TAIL_LOGS=0
DRY_RUN=0
LIST_ONLY=0
KEEP_COVERAGE_FILES=0
DISABLE_COVERAGE=0
SKIP_PREFLIGHT="${BIOETL_SKIP_PREFLIGHT:-0}"
STRICT_DOCS_PREFLIGHT="${BIOETL_PREFLIGHT_STRICT_DOCS:-0}"
SELECTED_WAVE=""
SELECTED_SHARDS=()
EXTRA_PYTEST_ARGS=()
SHARD_ORDER=()
declare -A SHARD_WAVE=()
declare -A SHARD_PATHS=()
declare -A SHARD_WORKERS_OVERRIDE=()
declare -A SHARD_EXTRA_PYTEST_ARGS=()
declare -A SHARD_ALIASES=()

usage() {
    cat <<'EOF'
Usage:
  bash scripts/engineering/dev/run_pytest_sharded.sh [options] [-- <extra pytest args>]

Purpose:
  Run the repo's large pytest suite through stable path-based shards using the
  maintained wrapper `scripts/engineering/dev/run_pytest.sh`.

Options:
  --list                    Show shard plan and exit
  --wave N                  Run only one wave (1, 2, 3, or 4)
  --shard NAME              Run only the named shard (may be repeated)
  --workers-per-shard N     xdist workers per shard (default: 2)
  --dist MODE               xdist distribution mode (default: loadfile)
  --coverage-dir PATH       Directory for per-shard coverage files
  --coverage-report-dir PATH
                            Directory for combined coverage XML/HTML artifacts
  --junit-dir PATH          Directory for per-shard JUnit XML files
                            (default: reports/quality/test-runs/junit/run-TIMESTAMP)
  --force-mounted-coverage  Keep pytest-cov enabled on /mnt/* checkouts and
                            move raw per-shard coverage files to /tmp when needed
  --stream                  Stream live shard output to console and log file
  --tail                    Tail shard log files live with shard prefixes
                            Ignored when --stream is also set
  --dry-run                 Print commands without executing them
  --skip-preflight          Skip repository/docs/architecture preflight
  --keep-coverage-files     Do not clean the coverage directory before/after
  -h, --help                Show this help

Examples:
  bash scripts/engineering/dev/run_pytest_sharded.sh
  bash scripts/engineering/dev/run_pytest_sharded.sh --stream
  bash scripts/engineering/dev/run_pytest_sharded.sh --tail
  bash scripts/engineering/dev/run_pytest_sharded.sh --wave 2
  bash scripts/engineering/dev/run_pytest_sharded.sh --shard S3-app-foundation -- --lf
EOF
    return 0
}

selected_yaml_python() {
    local python_bin
    if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]] && python_has_modules "$BIOETL_PYTEST_RUNTIME_PYTHON" yaml; then
        printf '%s\n' "$BIOETL_PYTEST_RUNTIME_PYTHON"
        return 0
    fi
    if [[ -x "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" ]]; then
        python_bin="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
        if python_has_modules "$python_bin" yaml; then
            printf '%s\n' "$python_bin"
            return 0
        fi
    fi
    if [[ -x ".venv/bin/python" ]]; then
        python_bin="$REPO_ROOT/.venv/bin/python"
        if python_has_modules "$python_bin" yaml; then
            printf '%s\n' "$python_bin"
            return 0
        fi
    fi
    if command -v python3 >/dev/null 2>&1; then
        python_bin="$(command -v python3)"
        if python_has_modules "$python_bin" yaml; then
            printf '%s\n' "$python_bin"
            return 0
        fi
    fi
    if command -v python >/dev/null 2>&1; then
        python_bin="$(command -v python)"
        if python_has_modules "$python_bin" yaml; then
            printf '%s\n' "$python_bin"
            return 0
        fi
    fi
    return 1
}

load_shard_inventory() {
    local python_bin
    python_bin="$(selected_yaml_python)" || {
        echo "[run_pytest_sharded][error] No Python with PyYAML available for shard inventory loading." >&2
        exit 2
    }
    [[ -f "$INVENTORY_PATH" ]] || {
        echo "[run_pytest_sharded][error] Missing shard inventory: $INVENTORY_PATH" >&2
        exit 2
    }

    SHARD_ORDER=()
    SHARD_WAVE=()
    SHARD_PATHS=()
    SHARD_WORKERS_OVERRIDE=()
    SHARD_EXTRA_PYTEST_ARGS=()
    SHARD_ALIASES=()

    # shellcheck disable=SC2016
    eval "$(
        "$python_bin" - "$INVENTORY_PATH" <<'PY'
from __future__ import annotations

import shlex
import sys
from pathlib import Path

import yaml


def q(value: str) -> str:
    return shlex.quote(value)


inventory_path = Path(sys.argv[1])
payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
if not isinstance(payload, dict):
    raise SystemExit("Shard inventory must be a mapping.")
if payload.get("schema_version") != 1:
    raise SystemExit("Shard inventory schema_version must be 1.")

shards = payload.get("shards")
if not isinstance(shards, list) or not shards:
    raise SystemExit("Shard inventory must declare a non-empty shards list.")

seen_names: set[str] = set()
for shard in shards:
    if not isinstance(shard, dict):
        raise SystemExit("Each shard definition must be a mapping.")
    name = shard.get("name")
    wave = shard.get("wave")
    paths = shard.get("paths")
    if not isinstance(name, str) or not name:
        raise SystemExit("Each shard must declare a non-empty name.")
    if name in seen_names:
        raise SystemExit(f"Duplicate shard name: {name}")
    seen_names.add(name)
    if not isinstance(wave, int):
        raise SystemExit(f"Shard {name} must declare integer wave.")
    if not isinstance(paths, list) or not all(isinstance(path, str) and path for path in paths):
        raise SystemExit(f"Shard {name} must declare non-empty string paths.")
    workers_override = shard.get("workers_override")
    if workers_override is not None and not isinstance(workers_override, int):
        raise SystemExit(f"Shard {name} workers_override must be an integer when present.")
    extra_args = shard.get("extra_pytest_args", [])
    if not isinstance(extra_args, list) or not all(
        isinstance(arg, str) and arg for arg in extra_args
    ):
        raise SystemExit(
            f"Shard {name} extra_pytest_args must be a list of non-empty strings."
        )
    print(f'SHARD_ORDER+=({q(name)})')
    print(f'SHARD_WAVE[{q(name)}]={q(str(wave))}')
    print(f'SHARD_PATHS[{q(name)}]={q(" ".join(paths))}')
    if workers_override is not None:
        print(f'SHARD_WORKERS_OVERRIDE[{q(name)}]={q(str(workers_override))}')
    if extra_args:
        print(f'SHARD_EXTRA_PYTEST_ARGS[{q(name)}]={q(" ".join(extra_args))}')

aliases = payload.get("aliases", {})
if aliases is None:
    aliases = {}
if not isinstance(aliases, dict):
    raise SystemExit("Shard inventory aliases must be a mapping when present.")

for alias, config in aliases.items():
    if not isinstance(alias, str) or not alias:
        raise SystemExit("Alias names must be non-empty strings.")
    if not isinstance(config, dict):
        raise SystemExit(f"Alias {alias} must be a mapping.")
    expands_to = config.get("expands_to")
    if not isinstance(expands_to, list) or not expands_to:
        raise SystemExit(f"Alias {alias} must declare a non-empty expands_to list.")
    if not all(isinstance(target, str) and target for target in expands_to):
        raise SystemExit(f"Alias {alias} expands_to entries must be non-empty strings.")
    missing = sorted(target for target in expands_to if target not in seen_names)
    if missing:
        raise SystemExit(f"Alias {alias} references unknown shards: {', '.join(missing)}")
    print(f'SHARD_ALIASES[{q(alias)}]={q(" ".join(expands_to))}')
PY
    )"
    return 0
}

is_valid_shard() {
    local wanted="$1"
    if [[ -n "${SHARD_ALIASES[$wanted]:-}" ]]; then
        return 0
    fi

    local shard
    for shard in "${SHARD_ORDER[@]}"; do
        if [[ "$shard" == "$wanted" ]]; then
            return 0
        fi
    done
    return 1
}

expand_shard_alias() {
    local shard="$1"
    if [[ -n "${SHARD_ALIASES[$shard]:-}" ]]; then
        # shellcheck disable=SC2206
        local -a expanded=( ${SHARD_ALIASES[$shard]} )
        printf '%s\n' "${expanded[@]}"
        return 0
    fi
    printf '%s\n' "$shard"
    return 0
}

parse_args() {
    while (($# > 0)); do
        local current_arg="$1"
        local current_value="${2:-}"
        case "$current_arg" in
            --list)
                LIST_ONLY=1
                shift
                ;;
            --wave)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --wave requires a value" >&2
                    exit 2
                }
                SELECTED_WAVE="$current_value"
                shift 2
                ;;
            --shard)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --shard requires a value" >&2
                    exit 2
                }
                is_valid_shard "$current_value" || {
                    echo "[run_pytest_sharded][error] Unknown shard: $current_value" >&2
                    exit 2
                }
                local expanded_shard
                while IFS= read -r expanded_shard; do
                    SELECTED_SHARDS+=("$expanded_shard")
                done < <(expand_shard_alias "$current_value")
                shift 2
                ;;
            --workers-per-shard)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --workers-per-shard requires a value" >&2
                    exit 2
                }
                WORKERS_PER_SHARD="$current_value"
                shift 2
                ;;
            --dist)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --dist requires a value" >&2
                    exit 2
                }
                DIST_MODE="$current_value"
                shift 2
                ;;
            --coverage-dir)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --coverage-dir requires a value" >&2
                    exit 2
                }
                COVERAGE_DIR="$current_value"
                shift 2
                ;;
            --coverage-report-dir)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --coverage-report-dir requires a value" >&2
                    exit 2
                }
                COVERAGE_REPORT_DIR="$current_value"
                shift 2
                ;;
            --junit-dir)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --junit-dir requires a value" >&2
                    exit 2
                }
                JUNIT_DIR="$current_value"
                shift 2
                ;;
            --force-mounted-coverage)
                FORCE_MOUNTED_COVERAGE=1
                shift
                ;;
            --stream)
                STREAM_LOGS=1
                shift
                ;;
            --tail)
                TAIL_LOGS=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --skip-preflight)
                SKIP_PREFLIGHT=1
                shift
                ;;
            --keep-coverage-files)
                KEEP_COVERAGE_FILES=1
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            --)
                shift
                EXTRA_PYTEST_ARGS=("$@")
                break
                ;;
            *)
                echo "[run_pytest_sharded][error] Unknown argument: $current_arg" >&2
                usage >&2
                exit 2
                ;;
        esac
    done
    return 0
}

print_plan() {
    local shard
    printf "Shard plan for path-based pytest runs\n"
    printf "Workers per shard: %s\n" "$WORKERS_PER_SHARD"
    printf "xdist distribution: %s\n\n" "$DIST_MODE"
    for shard in "${SHARD_ORDER[@]}"; do
        printf "%s  wave=%s  paths=%s\n" \
            "$shard" \
            "${SHARD_WAVE[$shard]}" \
            "${SHARD_PATHS[$shard]}"
    done
    return 0
}

build_selected_shards() {
    local shard
    local selected=()

    if ((${#SELECTED_SHARDS[@]} > 0)); then
        selected=("${SELECTED_SHARDS[@]}")
    else
        for shard in "${SHARD_ORDER[@]}"; do
            if [[ -n "$SELECTED_WAVE" && "${SHARD_WAVE[$shard]}" != "$SELECTED_WAVE" ]]; then
                continue
            fi
            selected+=("$shard")
        done
    fi

    if ((${#selected[@]} == 0)); then
        echo "[run_pytest_sharded][error] No shards selected." >&2
        exit 2
    fi

    printf '%s\n' "${selected[@]}"
    return 0
}

workers_for_shard() {
    local shard="$1"
    if [[ -n "${SHARD_WORKERS_OVERRIDE[$shard]:-}" ]]; then
        printf '%s\n' "${SHARD_WORKERS_OVERRIDE[$shard]}"
        return 0
    fi
    printf '%s\n' "$WORKERS_PER_SHARD"
    return 0
}

python_has_modules() {
    local python_bin="$1"
    shift

    [[ -x "$python_bin" ]] || return 1
    "$python_bin" - "$@" <<'PY' >/dev/null 2>&1
from __future__ import annotations

import importlib.util
import sys

raise SystemExit(
    0
    if all(importlib.util.find_spec(module) is not None for module in sys.argv[1:])
    else 1
)
PY
    return $?
}

windows_venv_supports_pytest_cov() {
    python_has_modules ".venv-win/Scripts/python.exe" pytest pytest_cov coverage
    return $?
}

selected_python() {
    if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]] && python_has_modules "$BIOETL_PYTEST_RUNTIME_PYTHON" coverage; then
        printf '%s\n' "$BIOETL_PYTEST_RUNTIME_PYTHON"
        return 0
    fi
    if [[ -x "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" ]]; then
        local wsl_python="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
        if python_has_modules "$wsl_python" coverage; then
            printf '%s\n' "$wsl_python"
            return 0
        fi
    fi
    if [[ -x ".venv/bin/python" ]]; then
        local repo_python="$REPO_ROOT/.venv/bin/python"
        if python_has_modules "$repo_python" coverage; then
            printf '%s\n' "$repo_python"
            return 0
        fi
    fi
    if command -v python3 >/dev/null 2>&1; then
        local system_python3
        system_python3="$(command -v python3)"
        if python_has_modules "$system_python3" coverage; then
            printf '%s\n' "$system_python3"
            return 0
        fi
    fi
    if command -v python >/dev/null 2>&1; then
        local system_python
        system_python="$(command -v python)"
        if python_has_modules "$system_python" coverage; then
            printf '%s\n' "$system_python"
            return 0
        fi
    fi
    if windows_venv_supports_pytest_cov; then
        printf '%s\n' "$REPO_ROOT/.venv-win/Scripts/python.exe"
        return 0
    fi
    return 1
}

selected_test_health_python() {
    selected_yaml_python
    return $?
}

shell_join() {
    local arg
    local first=1
    for arg in "$@"; do
        if [[ "$first" == "0" ]]; then
            printf ' '
        fi
        printf '%q' "$arg"
        first=0
    done
    return 0
}

is_wsl_mounted_checkout() {
    [[ "$REPO_ROOT" == /mnt/* ]]
    return $?
}

coverage_dir_targets_mounted_checkout() {
    if [[ "$COVERAGE_DIR" != /* ]]; then
        return 0
    fi
    [[ "$COVERAGE_DIR" == /mnt/* ]]
    return $?
}

default_tmp_coverage_dir() {
    local repo_name
    repo_name="$(basename "$REPO_ROOT")"
    printf '/tmp/%s-sharded-coverage-%s-%s\n' \
        "$repo_name" \
        "$(date +%Y%m%d-%H%M%S)" \
        "$$"
    return 0
}

default_tmp_hypothesis_database_dir() {
    local repo_name
    repo_name="$(basename "$REPO_ROOT")"
    printf '/tmp/%s-hypothesis-db-%s-%s\n' \
        "$repo_name" \
        "$(date +%Y%m%d-%H%M%S)" \
        "$$"
    return 0
}

normalize_coverage_dir_for_environment() {
    if ! is_wsl_mounted_checkout; then
        return 0
    fi

    if [[ "$FORCE_MOUNTED_COVERAGE" == "1" ]]; then
        if [[ "$COVERAGE_DIR" == "$DEFAULT_COVERAGE_DIR" ]] || coverage_dir_targets_mounted_checkout; then
            local requested_coverage_dir="$COVERAGE_DIR"
            COVERAGE_DIR="$(default_tmp_coverage_dir)"
            echo \
                "[run_pytest_sharded][info] Using temp raw coverage dir $COVERAGE_DIR for mounted WSL checkout $REPO_ROOT (requested: $requested_coverage_dir)" \
                >&2
        fi
        echo \
            "[run_pytest_sharded][info] Keeping pytest-cov enabled on mounted WSL checkout because --force-mounted-coverage / BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 was requested. Combined reports will be written under $COVERAGE_REPORT_DIR" \
            >&2
        return 0
    fi

    if [[ "$COVERAGE_DIR" == "$DEFAULT_COVERAGE_DIR" ]]; then
        COVERAGE_DIR="$(default_tmp_coverage_dir)"
        echo \
            "[run_pytest_sharded][info] Using temp coverage dir $COVERAGE_DIR for mounted WSL checkout $REPO_ROOT" \
            >&2
    fi

    DISABLE_COVERAGE=1
    echo \
        "[run_pytest_sharded][info] Disabling pytest-cov for mounted WSL checkout to avoid coverage instability under /mnt/* (including sqlite lock/malformed shard data). Use --force-mounted-coverage or BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 to keep coverage enabled and persist combined reports under $COVERAGE_REPORT_DIR" \
        >&2
    return 0
}

prepare_hypothesis_database_for_environment() {
    if [[ -n "${HYPOTHESIS_DATABASE:-}" ]]; then
        return 0
    fi

    if ! is_wsl_mounted_checkout; then
        return 0
    fi

    HYPOTHESIS_DATABASE="$(default_tmp_hypothesis_database_dir)"
    mkdir -p "$HYPOTHESIS_DATABASE"
    export HYPOTHESIS_DATABASE
    echo "[run_pytest_sharded][info] Using temp Hypothesis database $HYPOTHESIS_DATABASE for mounted WSL checkout $REPO_ROOT" >&2
    return 0
}

run_preflight_if_needed() {
    if [[ "$SKIP_PREFLIGHT" == "1" || "${BIOETL_PREFLIGHT_DONE:-0}" == "1" || "${BIOETL_PREFLIGHT_ACTIVE:-0}" == "1" ]]; then
        return 0
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "[run_pytest_sharded][info] Dry-run mode: preflight skipped." >&2
        return 0
    fi

    if [[ ! -f "$SCRIPT_DIR/pretest_guardrails.sh" ]]; then
        return 0
    fi

    local -a preflight_cmd=(
        bash "$SCRIPT_DIR/pretest_guardrails.sh"
        --mode auto
        --scope full
    )
    if [[ "$STRICT_DOCS_PREFLIGHT" == "1" ]]; then
        preflight_cmd+=(--strict-docs)
    fi

    BIOETL_PREFLIGHT_ACTIVE=1 "${preflight_cmd[@]}"
    export BIOETL_PREFLIGHT_DONE=1
    return 0
}

cleanup_coverage_dir() {
    if [[ "$KEEP_COVERAGE_FILES" == "1" ]]; then
        mkdir -p "$COVERAGE_DIR"
        rm -f "$COVERAGE_DIR"/.coverage "$COVERAGE_DIR"/.coverage.* 2>/dev/null || true
        return 0
    fi
    if rm -rf "$COVERAGE_DIR" 2>/dev/null; then
        return 0
    fi

    if [[ "$COVERAGE_DIR" == "$DEFAULT_COVERAGE_DIR" ]]; then
        local fallback_dir="/tmp/bioetl-sharded-coverage-$(date +%Y%m%d-%H%M%S)-$$"
        echo \
            "[run_pytest_sharded][warn] Could not clean $DEFAULT_COVERAGE_DIR; using fallback coverage dir $fallback_dir" \
            >&2
        COVERAGE_DIR="$fallback_dir"
        return 0
    fi

    echo "[run_pytest_sharded][error] Could not clean coverage dir: $COVERAGE_DIR" >&2
    return 1
}

start_log_tailer() {
    local shard="$1"
    local log_file="$2"

    touch "$log_file"
    tail -n +1 -f "$log_file" 2>/dev/null | sed -u "s/^/[${shard}] /" &
    printf '%s\n' "$!"
    return 0
}

stop_log_tailers() {
    local tail_pid
    for tail_pid in "$@"; do
        if [[ -n "$tail_pid" ]] && kill -0 "$tail_pid" 2>/dev/null; then
            kill "$tail_pid" 2>/dev/null || true
            wait "$tail_pid" 2>/dev/null || true
        fi
    done
    return 0
}

run_wave() {
    local wave="$1"
    shift
    local shards=("$@")
    local -a pids=()
    local -a labels=()
    local -a logs=()
    local -a tail_pids=()
    local shard

    mkdir -p "$COVERAGE_DIR/logs"
    if [[ -n "$JUNIT_DIR" ]]; then
        mkdir -p "$JUNIT_DIR"
    fi

    printf "\n[run_pytest_sharded] Starting wave %s\n" "$wave"

    for shard in "${shards[@]}"; do
        local paths_string="${SHARD_PATHS[$shard]}"
        local coverage_file="$COVERAGE_DIR/.coverage.$shard"
        local log_file="$COVERAGE_DIR/logs/$shard.log"
        local -a cmd=(bash "$RUNNER")
        local shard_extra_args_string="${SHARD_EXTRA_PYTEST_ARGS[$shard]:-}"
        local shard_workers

        # shellcheck disable=SC2206
        local -a paths=( $paths_string )
        # shellcheck disable=SC2206
        local -a shard_extra_args=( $shard_extra_args_string )
        cmd+=("${paths[@]}")
        shard_workers="$(workers_for_shard "$shard")"
        if [[ "$shard_workers" =~ ^[0-9]+$ ]] && (( shard_workers > 0 )); then
            cmd+=(-n "$shard_workers")
        fi
        if [[ -n "$DIST_MODE" && "$shard_workers" =~ ^[0-9]+$ && "$shard_workers" -gt 0 ]]; then
            cmd+=(--dist="$DIST_MODE")
        fi
        if [[ "$DISABLE_COVERAGE" == "1" ]]; then
            cmd+=(--no-cov)
        fi
        cmd+=("${shard_extra_args[@]}")
        if [[ -n "$JUNIT_DIR" ]]; then
            cmd+=("--junitxml=$JUNIT_DIR/$shard.xml")
        fi
        cmd+=(-o "cache_dir=$PYTEST_CACHE_DIR")
        cmd+=("${EXTRA_PYTEST_ARGS[@]}")

        if [[ "$DRY_RUN" == "1" ]]; then
            printf "[dry-run] COVERAGE_FILE=%s %q" "$coverage_file" "${cmd[0]}"
            local arg
            for arg in "${cmd[@]:1}"; do
                printf " %q" "$arg"
            done
            printf "\n"
            continue
        fi

        printf "[run_pytest_sharded] %s -> %s\n" "$shard" "$log_file"
        : >"$log_file"

        if [[ "$TAIL_LOGS" == "1" && "$STREAM_LOGS" != "1" ]]; then
            tail_pids+=("$(start_log_tailer "$shard" "$log_file")")
        fi

        if [[ "$STREAM_LOGS" == "1" ]]; then
            (
                set -o pipefail
                export COVERAGE_FILE="$coverage_file"
                export PYTHONUNBUFFERED=1
                export BIOETL_PYTEST_LIVE_OUTPUT=1
                export BIOETL_SKIP_PREFLIGHT="$SKIP_PREFLIGHT"
                "${cmd[@]}" 2>&1 | tee "$log_file" | sed -u "s/^/[${shard}] /"
            ) &
        else
            (
                export COVERAGE_FILE="$coverage_file"
                export BIOETL_SKIP_PREFLIGHT="$SKIP_PREFLIGHT"
                if [[ "$TAIL_LOGS" == "1" ]]; then
                    export PYTHONUNBUFFERED=1
                    export BIOETL_PYTEST_LIVE_OUTPUT=1
                fi
                "${cmd[@]}"
            ) >"$log_file" 2>&1 &
        fi

        pids+=("$!")
        labels+=("$shard")
        logs+=("$log_file")
    done

    if [[ "$DRY_RUN" == "1" ]]; then
        return 0
    fi

    local failures=0
    local i
    for i in "${!pids[@]}"; do
        if ! wait "${pids[$i]}"; then
            failures=1
            printf "[run_pytest_sharded][fail] %s failed. Tail of %s:\n" "${labels[$i]}" "${logs[$i]}" >&2
            tail -40 "${logs[$i]}" >&2 || true
        else
            printf "[run_pytest_sharded][ok] %s completed\n" "${labels[$i]}"
        fi
    done

    if ((${#tail_pids[@]} > 0)); then
        stop_log_tailers "${tail_pids[@]}"
    fi

    if [[ "$failures" != "0" ]]; then
        return 1
    fi
    return 0
}

combine_coverage() {
    [[ "$DRY_RUN" == "0" ]] || return 0

    if [[ "$DISABLE_COVERAGE" == "1" ]]; then
        echo "[run_pytest_sharded][info] Coverage combine skipped because pytest-cov is disabled for this environment." >&2
        return 0
    fi

    local python_bin
    python_bin="$(selected_python)" || {
        echo "[run_pytest_sharded][warn] Could not find Python for coverage combine." >&2
        return 0
    }

    if [[ ! -d "$COVERAGE_DIR" ]]; then
        echo "[run_pytest_sharded][warn] Coverage directory does not exist: $COVERAGE_DIR" >&2
        return 0
    fi

    if ! compgen -G "$COVERAGE_DIR/.coverage.*" >/dev/null; then
        echo "[run_pytest_sharded][warn] No per-shard coverage files found under $COVERAGE_DIR" >&2
        return 0
    fi

    printf "\n[run_pytest_sharded] Combining coverage files from %s\n" "$COVERAGE_DIR"
    COVERAGE_FILE="$COVERAGE_DIR/.coverage" "$python_bin" -m coverage combine "$COVERAGE_DIR"
    COVERAGE_FILE="$COVERAGE_DIR/.coverage" "$python_bin" -m coverage report
    mkdir -p "$COVERAGE_REPORT_DIR"
    rm -f "$COVERAGE_REPORT_DIR/coverage.xml" 2>/dev/null || true
    rm -rf "$COVERAGE_REPORT_DIR/htmlcov" 2>/dev/null || true
    COVERAGE_FILE="$COVERAGE_DIR/.coverage" "$python_bin" -m coverage xml -o "$COVERAGE_REPORT_DIR/coverage.xml"
    COVERAGE_FILE="$COVERAGE_DIR/.coverage" "$python_bin" -m coverage html -d "$COVERAGE_REPORT_DIR/htmlcov"
    echo "[run_pytest_sharded][ok] Coverage XML: $COVERAGE_REPORT_DIR/coverage.xml"
    echo "[run_pytest_sharded][ok] Coverage HTML: $COVERAGE_REPORT_DIR/htmlcov/index.html"
    return 0
}

collect_test_health_summary() {
    local exit_code="$1"
    shift

    [[ "$DRY_RUN" == "0" ]] || return 0
    [[ "${BIOETL_PYTEST_SHARDED_TEST_HEALTH:-1}" != "0" ]] || return 0
    [[ "${BIOETL_TEST_HEALTH_WRAPPER:-0}" != "1" ]] || return 0

    if [[ -z "$JUNIT_DIR" || ! -d "$JUNIT_DIR" ]]; then
        echo "[run_pytest_sharded][warn] Test-health summary skipped: JUnit directory does not exist: $JUNIT_DIR" >&2
        return 0
    fi
    if ! compgen -G "$JUNIT_DIR/*.xml" >/dev/null; then
        echo "[run_pytest_sharded][warn] Test-health summary skipped: no JUnit XML files found in $JUNIT_DIR" >&2
        return 0
    fi

    local python_bin
    python_bin="$(selected_test_health_python)" || {
        echo "[run_pytest_sharded][warn] Test-health summary skipped: no Python with PyYAML available." >&2
        return 0
    }

    local run_id
    run_id="$(basename "$JUNIT_DIR")"
    local command_display
    command_display="$(shell_join bash scripts/engineering/dev/run_pytest_sharded.sh "$@")"

    local -a test_health_cmd=(
        "$python_bin" -m scripts.engineering.qa test-health
        --suite "$TEST_HEALTH_SUITE" \
        --run-id "$run_id" \
        --reports-dir "$TEST_HEALTH_REPORTS_DIR" \
        --junit-glob "$JUNIT_DIR/*.xml" \
        --command "$command_display" \
        --exit-code "$exit_code" \
        --last 30 \
        --markdown-out "$TEST_HEALTH_ROLLUP_MD"
    )

    if command -v timeout >/dev/null 2>&1; then
        timeout "${TEST_HEALTH_TIMEOUT_SECONDS}s" "${test_health_cmd[@]}" || {
            echo "[run_pytest_sharded][warn] Test-health summary generation failed or timed out." >&2
            return 0
        }
    else
        "${test_health_cmd[@]}" || {
            echo "[run_pytest_sharded][warn] Test-health summary generation failed." >&2
            return 0
        }
    fi
    return 0
}

main() {
    local -a original_args=("$@")
    load_shard_inventory
    parse_args "$@"
    if [[ "$LIST_ONLY" == "1" ]]; then
        print_plan
        exit 0
    fi

    run_preflight_if_needed
    normalize_coverage_dir_for_environment
    prepare_hypothesis_database_for_environment

    local -a selected_shards=()
    while IFS= read -r shard; do
        selected_shards+=("$shard")
    done < <(build_selected_shards)

    print_plan

    cleanup_coverage_dir
    mkdir -p "$COVERAGE_DIR"
    mkdir -p "$PYTEST_CACHE_DIR"

    local current_wave=""
    local -a wave_shards=()
    local shard
    local exit_code=0
    local stop_after_wave=0

    for shard in "${selected_shards[@]}"; do
        if [[ "$stop_after_wave" == "1" ]]; then
            break
        fi
        if [[ -z "$current_wave" ]]; then
            current_wave="${SHARD_WAVE[$shard]}"
        fi
        if [[ "${SHARD_WAVE[$shard]}" != "$current_wave" ]]; then
            if ! run_wave "$current_wave" "${wave_shards[@]}"; then
                exit_code=1
                stop_after_wave=1
                break
            fi
            wave_shards=()
            current_wave="${SHARD_WAVE[$shard]}"
        fi
        wave_shards+=("$shard")
    done

    if [[ "$stop_after_wave" != "1" ]] \
        && ((${#wave_shards[@]} > 0)) \
        && ! run_wave "$current_wave" "${wave_shards[@]}"; then
        exit_code=1
    fi

    if [[ "$exit_code" == "0" ]]; then
        combine_coverage
    fi
    collect_test_health_summary "$exit_code" "${original_args[@]}"

    if [[ "$DRY_RUN" == "0" ]]; then
        printf "\n[run_pytest_sharded] Done. Logs and coverage files: %s\n" "$COVERAGE_DIR"
        if [[ -n "$JUNIT_DIR" ]]; then
            printf "[run_pytest_sharded] JUnit reports: %s\n" "$JUNIT_DIR"
        fi
    fi
    return "$exit_code"
}

main "$@"
