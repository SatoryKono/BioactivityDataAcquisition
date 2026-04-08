#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

MODE="auto"
SCOPE="light"
STRICT_DOCS=0
SKIP_CLEANUP=0
SKIP_REPO=0
SKIP_DOCS=0
SKIP_ARCHITECTURE=0
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage:
  bash scripts/dev/pretest_guardrails.sh [options]

Purpose:
  Run the fast repository preflight that catches common docs/governance/
  architecture regressions before the full pytest suite starts.

Options:
  --mode auto|check       auto: refresh deterministic repo metadata before checks
                          check: validate only (default: auto)
  --scope light|full      light: cleanup + repo/docs checks
                          full: light checks + targeted architecture fail-fast
  --strict-docs           Run strict MkDocs build in docs verification
  --skip-cleanup          Skip cache/build artifact cleanup
  --skip-repo             Skip inventory/catalog governance checks
  --skip-docs             Skip docs verification
  --skip-architecture     Skip targeted architecture fail-fast checks
  --dry-run               Print commands without executing them
  -h, --help              Show this help
EOF
}

require_python() {
    if command -v python3 >/dev/null 2>&1; then
        printf '%s\n' "python3"
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        printf '%s\n' "python"
        return 0
    fi
    echo "[pretest-guardrails][error] Python runtime is not available." >&2
    return 1
}

run_step() {
    local label="$1"
    shift

    printf '[pretest-guardrails] %s: ' "$label"
    printf '%q ' "$@"
    printf '\n'

    if [[ "$DRY_RUN" == "1" ]]; then
        return 0
    fi

    "$@"
}

parse_args() {
    while (($# > 0)); do
        case "$1" in
            --mode)
                [[ $# -ge 2 ]] || {
                    echo "[pretest-guardrails][error] --mode requires a value" >&2
                    exit 2
                }
                MODE="$2"
                shift 2
                ;;
            --scope)
                [[ $# -ge 2 ]] || {
                    echo "[pretest-guardrails][error] --scope requires a value" >&2
                    exit 2
                }
                SCOPE="$2"
                shift 2
                ;;
            --strict-docs)
                STRICT_DOCS=1
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=1
                shift
                ;;
            --skip-repo)
                SKIP_REPO=1
                shift
                ;;
            --skip-docs)
                SKIP_DOCS=1
                shift
                ;;
            --skip-architecture)
                SKIP_ARCHITECTURE=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "[pretest-guardrails][error] Unknown argument: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
    done

    case "$MODE" in
        auto|check) ;;
        *)
            echo "[pretest-guardrails][error] Unsupported mode: $MODE" >&2
            exit 2
            ;;
    esac

    case "$SCOPE" in
        light|full) ;;
        *)
            echo "[pretest-guardrails][error] Unsupported scope: $SCOPE" >&2
            exit 2
            ;;
    esac
}

run_cleanup() {
    [[ "$SKIP_CLEANUP" == "0" ]] || return 0
    run_step cleanup env BIOETL_PREFLIGHT_PRESERVE_PYTEST_CACHE=1 bash scripts/repo/preflight_cleanup.sh
}

run_repo_checks() {
    [[ "$SKIP_REPO" == "0" ]] || return 0
    local python_bin
    python_bin="$(require_python)"

    if [[ "$MODE" == "auto" ]]; then
        run_step inventory-update \
            "$python_bin" -m scripts.repo check-inventory \
            --update \
            --manifest configs/quality/scripts_inventory_manifest.json
    fi

    run_step inventory-check \
        "$python_bin" -m scripts.repo check-inventory \
        --check \
        --manifest configs/quality/scripts_inventory_manifest.json \
        --check-lifecycle \
        --forbid-evaluate-active \
        --lifecycle-registry configs/quality/scripts_lifecycle_registry.json

    run_step catalog-check \
        "$python_bin" -m scripts.repo check-catalog \
        --catalog scripts/catalog.yaml
}

run_docs_checks() {
    [[ "$SKIP_DOCS" == "0" ]] || return 0
    local python_bin
    python_bin="$(require_python)"
    local -a cmd=("$python_bin" -m scripts.docs verify)
    if [[ "$STRICT_DOCS" != "1" ]]; then
        cmd+=(--skip-build)
    fi
    run_step docs-verify "${cmd[@]}"
}

run_architecture_checks() {
    [[ "$SKIP_ARCHITECTURE" == "0" ]] || return 0
    [[ "$SCOPE" == "full" ]] || return 0

    local -a cmd=(
        bash scripts/dev/run_pytest.sh
        --skip-preflight
        --narrow
        tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_every_test_surface_under_integration_and_e2e_is_in_tracked_inventory
        tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_testing_guide_matches_current_fixture_governance_and_live_contract_policy
        tests/architecture/test_documentation_sync.py::test_no_legacy_repo_slug_in_active_docs_and_workflows
        tests/architecture/test_scripts_catalog_governance.py::test_scripts_catalog_governance_check_passes
        tests/architecture/test_scripts_inventory_manifest.py::test_scripts_inventory_manifest_drift_check_passes
        tests/architecture/test_any_budget.py::test_any_budget_threshold
        tests/architecture/test_type_checking_density.py
        -q
        -x
        --tb=short
    )

    run_step architecture-fail-fast env \
        BIOETL_SKIP_PREFLIGHT=1 \
        BIOETL_PREFLIGHT_DONE=1 \
        "${cmd[@]}"
}

main() {
    parse_args "$@"

    echo "[pretest-guardrails] mode=$MODE scope=$SCOPE strict_docs=$STRICT_DOCS"

    run_cleanup
    run_repo_checks
    run_docs_checks
    run_architecture_checks

    echo "[pretest-guardrails] OK"
}

main "$@"
