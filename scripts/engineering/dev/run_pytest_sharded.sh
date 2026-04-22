#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
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
DEFAULT_WORKERS_PER_SHARD=2
DEFAULT_DIST_MODE="loadfile"
DEFAULT_COVERAGE_DIR="$REPO_ROOT/.coverage-sharded"
DEFAULT_PYTEST_CACHE_DIR="$REPO_ROOT/.pytest_cache"
DEFAULT_JUNIT_DIR="$REPO_ROOT/reports/quality/test-runs/junit/run-$(date +%Y%m%dT%H%M%S)"

WORKERS_PER_SHARD="$DEFAULT_WORKERS_PER_SHARD"
DIST_MODE="$DEFAULT_DIST_MODE"
COVERAGE_DIR="$DEFAULT_COVERAGE_DIR"
PYTEST_CACHE_DIR="$DEFAULT_PYTEST_CACHE_DIR"
JUNIT_DIR="$DEFAULT_JUNIT_DIR"
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
PATH_TESTS_ARCHITECTURE="tests/architecture"
SHARD_S1_DOMAIN_CORE="S1-domain-core"
SHARD_S1_DOMAIN_SERVICES="S1-domain-services"
SHARD_S2_COMP_IFACE="S2-comp-iface"
SHARD_S4_APP_SERVICES="S4-app-services"
SHARD_S7_ARCH_A="S7-crosscutting-architecture-a"
SHARD_S7_ARCH_B="S7-crosscutting-architecture-b"
SHARD_S7_ARCH_C="S7-crosscutting-architecture-c"
SHARD_S7_ARCH_D="S7-crosscutting-architecture-d"
SHARD_S7_GUARDRAILS="S7-crosscutting-architecture-guardrails"
SHARD_S8_GOVERNANCE="S8-crosscutting-governance"
SHARD_S9_FAILURES="S9-failures"

SHARD_ORDER=(
    "$SHARD_S1_DOMAIN_CORE"
    "$SHARD_S1_DOMAIN_SERVICES"
    "$SHARD_S2_COMP_IFACE"
    "$SHARD_S7_ARCH_A"
    "S3-app-foundation"
    "$SHARD_S4_APP_SERVICES"
    "$SHARD_S7_ARCH_B"
    "S5-infra-adapters"
    "S6-crosscutting-unit"
    "$SHARD_S7_ARCH_C"
    "$SHARD_S7_GUARDRAILS"
    "$SHARD_S8_GOVERNANCE"
    "$SHARD_S7_ARCH_D"
    "$SHARD_S9_FAILURES"
)

declare -A SHARD_WAVE=(
    ["$SHARD_S1_DOMAIN_CORE"]="1"
    ["$SHARD_S1_DOMAIN_SERVICES"]="1"
    ["$SHARD_S2_COMP_IFACE"]="1"
    ["$SHARD_S7_ARCH_A"]="1"
    ["S3-app-foundation"]="2"
    ["$SHARD_S4_APP_SERVICES"]="2"
    ["$SHARD_S7_ARCH_B"]="2"
    ["S5-infra-adapters"]="3"
    ["S6-crosscutting-unit"]="3"
    ["$SHARD_S7_ARCH_C"]="3"
    ["$SHARD_S7_GUARDRAILS"]="2"
    ["$SHARD_S8_GOVERNANCE"]="3"
    ["$SHARD_S7_ARCH_D"]="4"
    ["$SHARD_S9_FAILURES"]="4"
)

declare -A SHARD_PATHS=(
    ["S1-domain-core"]="tests/unit/domain/value_objects tests/unit/domain/schemas tests/unit/domain/entities tests/unit/domain/composite tests/unit/domain/filtering tests/unit/domain/types tests/unit/domain/ports tests/unit/domain/aggregates tests/unit/domain/validation tests/unit/domain/mapping tests/unit/domain/models tests/unit/domain/exceptions tests/unit/domain/transformations tests/unit/domain/lineage tests/unit/domain/hash_policy"
    ["S1-domain-services"]="tests/unit/domain/services tests/unit/domain/control_plane tests/unit/domain/config tests/unit/domain/configs tests/unit/domain/registry tests/unit/domain/test_*.py"
    ["$SHARD_S2_COMP_IFACE"]="tests/unit/composition tests/unit/interfaces"
    ["S3-app-foundation"]="tests/unit/application/composite tests/unit/application/core"
    ["$SHARD_S4_APP_SERVICES"]="tests/unit/application/services tests/unit/application/pipelines"
    ["S5-infra-adapters"]="tests/unit/infrastructure/adapters tests/unit/infrastructure/storage tests/integration/adapters tests/integration/interfaces"
    ["S6-crosscutting-unit"]="tests/unit/infrastructure/config tests/unit/infrastructure/quality tests/unit/infrastructure/observability tests/unit/infrastructure/schemas"
    ["$SHARD_S7_ARCH_A"]="$PATH_TESTS_ARCHITECTURE"
    ["$SHARD_S7_ARCH_B"]="$PATH_TESTS_ARCHITECTURE"
    ["$SHARD_S7_ARCH_C"]="$PATH_TESTS_ARCHITECTURE"
    ["$SHARD_S7_ARCH_D"]="$PATH_TESTS_ARCHITECTURE"
    ["$SHARD_S7_GUARDRAILS"]="tests/architecture/test_any_budget.py tests/architecture/test_scripts_catalog_governance.py tests/architecture/test_architecture_dependency_docs_drift.py tests/architecture/test_check_doc_links_guardrails.py tests/architecture/test_compatibility_facade_inventory.py tests/architecture/test_docs_version_sync.py tests/architecture/test_documentation_sync.py tests/architecture/test_code_metrics.py tests/architecture/test_legacy_schema_wrappers.py tests/architecture/test_diagram_regression_workflow.py tests/architecture/test_docs_governance_workflow.py tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_burndown_priorities.py"
    ["$SHARD_S8_GOVERNANCE"]="tests/integration/pipelines tests/integration/chembl tests/contract tests/smoke"
    ["$SHARD_S9_FAILURES"]="tests/unit/interfaces/cli/test_registry_consistency.py::TestListPipelinesCommandSnapshot::test_list_pipelines_command_output tests/unit/interfaces/cli/commands/test_quarantine_support.py::TestShowQuarantineStats::test_json_output_mode tests/architecture/test_provider_registry_decomposition.py::test_provider_registry_facade_does_not_grow tests/architecture/test_docs_governance_workflow.py::test_docs_workflow_runs_lightweight_docs_governance_profile tests/architecture/test_diagram_regression_workflow.py::test_docs_workflow_runs_doc_integrity_guardrails tests/architecture/test_rf014_composition_bootstrap_closeout.py::test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed[src/bioetl/composition/factories/pipeline/assembler.py-280-required_modules0]"
)

declare -A SHARD_WORKERS_OVERRIDE=(
    ["$SHARD_S1_DOMAIN_CORE"]="0"
    ["$SHARD_S1_DOMAIN_SERVICES"]="0"
    ["$SHARD_S4_APP_SERVICES"]="0"
    ["$SHARD_S7_ARCH_A"]="0"
    ["$SHARD_S7_ARCH_B"]="0"
    ["$SHARD_S7_ARCH_C"]="0"
    ["$SHARD_S7_ARCH_D"]="0"
    ["$SHARD_S7_GUARDRAILS"]="2"
    ["$SHARD_S8_GOVERNANCE"]="0"
    ["$SHARD_S9_FAILURES"]="0"
)

declare -A SHARD_EXTRA_PYTEST_ARGS=(
    ["$SHARD_S2_COMP_IFACE"]="--ignore=tests/unit/interfaces/cli/test_registry_consistency.py --deselect=tests/unit/interfaces/cli/commands/test_quarantine_support.py::TestShowQuarantineStats::test_json_output_mode --ignore=tests/unit/composition/runtime_builders/test_runner_builder.py --ignore=tests/unit/composition/runtime_builders/test_run_manifest_support.py"
    ["$SHARD_S7_ARCH_A"]="--timeout=300 --ignore-glob=tests/architecture/test_[g-z]*.py --ignore=tests/architecture/test_any_budget.py --ignore=tests/architecture/test_scripts_catalog_governance.py --ignore=tests/architecture/test_architecture_dependency_docs_drift.py --ignore=tests/architecture/test_check_doc_links_guardrails.py --ignore=tests/architecture/test_compatibility_facade_inventory.py --ignore=tests/architecture/test_docs_version_sync.py --ignore=tests/architecture/test_documentation_sync.py --ignore=tests/architecture/test_code_metrics.py --ignore=tests/architecture/test_legacy_schema_wrappers.py --ignore=tests/architecture/test_diagram_regression_workflow.py --ignore=tests/architecture/test_docs_governance_workflow.py --ignore=tests/architecture/test_quality_debt_scorecard.py --ignore=tests/architecture/test_quality_burndown_priorities.py --deselect=tests/architecture/test_provider_registry_decomposition.py::test_provider_registry_facade_does_not_grow --deselect=tests/architecture/test_rf014_composition_bootstrap_closeout.py::test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed[src/bioetl/composition/factories/pipeline/assembler.py-280-required_modules0]"
    ["$SHARD_S7_ARCH_B"]="--timeout=300 --ignore-glob=tests/architecture/test_[a-f]*.py --ignore-glob=tests/architecture/test_[m-z]*.py --ignore=tests/architecture/test_any_budget.py --ignore=tests/architecture/test_scripts_catalog_governance.py --ignore=tests/architecture/test_architecture_dependency_docs_drift.py --ignore=tests/architecture/test_check_doc_links_guardrails.py --ignore=tests/architecture/test_compatibility_facade_inventory.py --ignore=tests/architecture/test_docs_version_sync.py --ignore=tests/architecture/test_documentation_sync.py --ignore=tests/architecture/test_code_metrics.py --ignore=tests/architecture/test_legacy_schema_wrappers.py --ignore=tests/architecture/test_diagram_regression_workflow.py --ignore=tests/architecture/test_docs_governance_workflow.py --ignore=tests/architecture/test_quality_debt_scorecard.py --ignore=tests/architecture/test_quality_burndown_priorities.py --deselect=tests/architecture/test_provider_registry_decomposition.py::test_provider_registry_facade_does_not_grow --deselect=tests/architecture/test_rf014_composition_bootstrap_closeout.py::test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed[src/bioetl/composition/factories/pipeline/assembler.py-280-required_modules0]"
    ["$SHARD_S7_ARCH_C"]="--timeout=300 --ignore-glob=tests/architecture/test_[a-l]*.py --ignore-glob=tests/architecture/test_[s-z]*.py --ignore=tests/architecture/test_any_budget.py --ignore=tests/architecture/test_scripts_catalog_governance.py --ignore=tests/architecture/test_architecture_dependency_docs_drift.py --ignore=tests/architecture/test_check_doc_links_guardrails.py --ignore=tests/architecture/test_compatibility_facade_inventory.py --ignore=tests/architecture/test_docs_version_sync.py --ignore=tests/architecture/test_documentation_sync.py --ignore=tests/architecture/test_code_metrics.py --ignore=tests/architecture/test_legacy_schema_wrappers.py --ignore=tests/architecture/test_diagram_regression_workflow.py --ignore=tests/architecture/test_docs_governance_workflow.py --ignore=tests/architecture/test_quality_debt_scorecard.py --ignore=tests/architecture/test_quality_burndown_priorities.py --deselect=tests/architecture/test_provider_registry_decomposition.py::test_provider_registry_facade_does_not_grow --deselect=tests/architecture/test_rf014_composition_bootstrap_closeout.py::test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed[src/bioetl/composition/factories/pipeline/assembler.py-280-required_modules0]"
    ["$SHARD_S7_ARCH_D"]="--timeout=300 --ignore-glob=tests/architecture/test_[a-r]*.py --ignore=tests/architecture/test_any_budget.py --ignore=tests/architecture/test_scripts_catalog_governance.py --ignore=tests/architecture/test_architecture_dependency_docs_drift.py --ignore=tests/architecture/test_check_doc_links_guardrails.py --ignore=tests/architecture/test_compatibility_facade_inventory.py --ignore=tests/architecture/test_docs_version_sync.py --ignore=tests/architecture/test_documentation_sync.py --ignore=tests/architecture/test_code_metrics.py --ignore=tests/architecture/test_legacy_schema_wrappers.py --ignore=tests/architecture/test_diagram_regression_workflow.py --ignore=tests/architecture/test_docs_governance_workflow.py --ignore=tests/architecture/test_quality_debt_scorecard.py --ignore=tests/architecture/test_quality_burndown_priorities.py --deselect=tests/architecture/test_provider_registry_decomposition.py::test_provider_registry_facade_does_not_grow --deselect=tests/architecture/test_rf014_composition_bootstrap_closeout.py::test_rf014_composition_bootstrap_surfaces_stay_bounded_and_helper_backed[src/bioetl/composition/factories/pipeline/assembler.py-280-required_modules0]"
    ["$SHARD_S7_GUARDRAILS"]="--timeout=300 --deselect=tests/architecture/test_docs_governance_workflow.py::test_docs_workflow_runs_lightweight_docs_governance_profile --deselect=tests/architecture/test_diagram_regression_workflow.py::test_docs_workflow_runs_doc_integrity_guardrails"
    ["$SHARD_S8_GOVERNANCE"]="--timeout=300"
    ["$SHARD_S9_FAILURES"]="--timeout=300"
)

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
  --junit-dir PATH          Directory for per-shard JUnit XML files
                            (default: reports/quality/test-runs/junit/run-TIMESTAMP)
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

is_valid_shard() {
    local wanted="$1"

    # Backward-compatible alias for the pre-split S7 shard.
    if [[ "$wanted" == "S7-crosscutting-architecture" ]]; then
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
    case "$shard" in
        S7-crosscutting-architecture)
            printf '%s\n' \
                "S7-crosscutting-architecture-a" \
                "S7-crosscutting-architecture-b" \
                "S7-crosscutting-architecture-c" \
                "S7-crosscutting-architecture-d"
            ;;
        *)
            printf '%s\n' "$shard"
            ;;
    esac
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
            --junit-dir)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --junit-dir requires a value" >&2
                    exit 2
                }
                JUNIT_DIR="$current_value"
                shift 2
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

is_wsl_mounted_checkout() {
    [[ "$REPO_ROOT" == /mnt/* ]]
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

    if [[ "$COVERAGE_DIR" == "$DEFAULT_COVERAGE_DIR" ]]; then
        COVERAGE_DIR="$(default_tmp_coverage_dir)"
        echo \
            "[run_pytest_sharded][info] Using temp coverage dir $COVERAGE_DIR for mounted WSL checkout $REPO_ROOT" \
            >&2
    fi

    DISABLE_COVERAGE=1
    echo \
        "[run_pytest_sharded][info] Disabling pytest-cov for mounted WSL checkout to avoid coverage instability under /mnt/* (including sqlite lock/malformed shard data)" \
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
    return 0
}

main() {
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

    for shard in "${selected_shards[@]}"; do
        if [[ -z "$current_wave" ]]; then
            current_wave="${SHARD_WAVE[$shard]}"
        fi
        if [[ "${SHARD_WAVE[$shard]}" != "$current_wave" ]]; then
            run_wave "$current_wave" "${wave_shards[@]}"
            wave_shards=()
            current_wave="${SHARD_WAVE[$shard]}"
        fi
        wave_shards+=("$shard")
    done

    if ((${#wave_shards[@]} > 0)); then
        run_wave "$current_wave" "${wave_shards[@]}"
    fi

    combine_coverage

    if [[ "$DRY_RUN" == "0" ]]; then
        printf "\n[run_pytest_sharded] Done. Logs and coverage files: %s\n" "$COVERAGE_DIR"
        if [[ -n "$JUNIT_DIR" ]]; then
            printf "[run_pytest_sharded] JUnit reports: %s\n" "$JUNIT_DIR"
        fi
    fi
    return 0
}

main "$@"
