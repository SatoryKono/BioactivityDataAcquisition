#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

RUNNER="$SCRIPT_DIR/run_pytest.sh"
DEFAULT_WORKERS_PER_SHARD=2
DEFAULT_DIST_MODE="loadfile"
DEFAULT_COVERAGE_DIR="$REPO_ROOT/.coverage-sharded"

WORKERS_PER_SHARD="$DEFAULT_WORKERS_PER_SHARD"
DIST_MODE="$DEFAULT_DIST_MODE"
COVERAGE_DIR="$DEFAULT_COVERAGE_DIR"
DRY_RUN=0
LIST_ONLY=0
KEEP_COVERAGE_FILES=0
SELECTED_WAVE=""
SELECTED_SHARDS=()
EXTRA_PYTEST_ARGS=()

SHARD_ORDER=(
    "S1-domain"
    "S2-comp-iface"
    "S3-app-foundation"
    "S4-app-services"
    "S5-infra-adapters"
    "S6-crosscutting-core"
)

declare -A SHARD_WAVE=(
    ["S1-domain"]="1"
    ["S2-comp-iface"]="1"
    ["S3-app-foundation"]="2"
    ["S4-app-services"]="2"
    ["S5-infra-adapters"]="3"
    ["S6-crosscutting-core"]="3"
)

declare -A SHARD_PATHS=(
    ["S1-domain"]="tests/unit/domain"
    ["S2-comp-iface"]="tests/unit/composition tests/unit/interfaces"
    ["S3-app-foundation"]="tests/unit/application/composite tests/unit/application/core"
    ["S4-app-services"]="tests/unit/application/services tests/unit/application/pipelines"
    ["S5-infra-adapters"]="tests/unit/infrastructure/adapters tests/unit/infrastructure/storage tests/integration/adapters tests/integration/interfaces"
    ["S6-crosscutting-core"]="tests/unit/infrastructure/config tests/unit/infrastructure/quality tests/unit/infrastructure/observability tests/unit/infrastructure/schemas tests/integration/pipelines tests/integration/chembl tests/architecture tests/contract tests/smoke"
)

usage() {
    cat <<'EOF'
Usage:
  bash scripts/dev/run_pytest_sharded.sh [options] [-- <extra pytest args>]

Purpose:
  Run the repo's large pytest suite through stable path-based shards using the
  maintained wrapper `scripts/dev/run_pytest.sh`.

Options:
  --list                    Show shard plan and exit
  --wave N                  Run only one wave (1, 2, or 3)
  --shard NAME              Run only the named shard (may be repeated)
  --workers-per-shard N     xdist workers per shard (default: 2)
  --dist MODE               xdist distribution mode (default: loadfile)
  --coverage-dir PATH       Directory for per-shard coverage files
  --dry-run                 Print commands without executing them
  --keep-coverage-files     Do not clean the coverage directory before/after
  -h, --help                Show this help

Examples:
  bash scripts/dev/run_pytest_sharded.sh
  bash scripts/dev/run_pytest_sharded.sh --wave 2
  bash scripts/dev/run_pytest_sharded.sh --shard S3-app-foundation -- --lf
EOF
}

is_valid_shard() {
    local wanted="$1"
    local shard
    for shard in "${SHARD_ORDER[@]}"; do
        if [[ "$shard" == "$wanted" ]]; then
            return 0
        fi
    done
    return 1
}

parse_args() {
    while (($# > 0)); do
        case "$1" in
            --list)
                LIST_ONLY=1
                shift
                ;;
            --wave)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --wave requires a value" >&2
                    exit 2
                }
                SELECTED_WAVE="$2"
                shift 2
                ;;
            --shard)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --shard requires a value" >&2
                    exit 2
                }
                is_valid_shard "$2" || {
                    echo "[run_pytest_sharded][error] Unknown shard: $2" >&2
                    exit 2
                }
                SELECTED_SHARDS+=("$2")
                shift 2
                ;;
            --workers-per-shard)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --workers-per-shard requires a value" >&2
                    exit 2
                }
                WORKERS_PER_SHARD="$2"
                shift 2
                ;;
            --dist)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --dist requires a value" >&2
                    exit 2
                }
                DIST_MODE="$2"
                shift 2
                ;;
            --coverage-dir)
                [[ $# -ge 2 ]] || {
                    echo "[run_pytest_sharded][error] --coverage-dir requires a value" >&2
                    exit 2
                }
                COVERAGE_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=1
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
                echo "[run_pytest_sharded][error] Unknown argument: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
    done
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
}

selected_python() {
    if [[ -x "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" ]]; then
        printf '%s\n' "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
        return 0
    fi
    if [[ -x ".venv/bin/python" ]]; then
        printf '%s\n' "$REPO_ROOT/.venv/bin/python"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi
    return 1
}

cleanup_coverage_dir() {
    if [[ "$KEEP_COVERAGE_FILES" == "1" ]]; then
        return 0
    fi
    rm -rf "$COVERAGE_DIR"
}

run_wave() {
    local wave="$1"
    shift
    local shards=("$@")
    local -a pids=()
    local -a labels=()
    local -a logs=()
    local shard

    mkdir -p "$COVERAGE_DIR/logs"

    printf "\n[run_pytest_sharded] Starting wave %s\n" "$wave"

    for shard in "${shards[@]}"; do
        local paths_string="${SHARD_PATHS[$shard]}"
        local coverage_file="$COVERAGE_DIR/.coverage.$shard"
        local log_file="$COVERAGE_DIR/logs/$shard.log"
        local -a cmd=(bash "$RUNNER")
        local path

        # shellcheck disable=SC2206
        local -a paths=( $paths_string )
        cmd+=("${paths[@]}")
        cmd+=(-n "$WORKERS_PER_SHARD")
        if [[ -n "$DIST_MODE" ]]; then
            cmd+=(--dist="$DIST_MODE")
        fi
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
        (
            export COVERAGE_FILE="$coverage_file"
            "${cmd[@]}"
        ) >"$log_file" 2>&1 &

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

    if [[ "$failures" != "0" ]]; then
        return 1
    fi
    return 0
}

combine_coverage() {
    [[ "$DRY_RUN" == "0" ]] || return 0

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
}

main() {
    parse_args "$@"

    if [[ "$LIST_ONLY" == "1" ]]; then
        print_plan
        exit 0
    fi

    local -a selected_shards=()
    while IFS= read -r shard; do
        selected_shards+=("$shard")
    done < <(build_selected_shards)

    print_plan

    cleanup_coverage_dir
    mkdir -p "$COVERAGE_DIR"

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
    fi
}

main "$@"
