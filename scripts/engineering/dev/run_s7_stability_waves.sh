#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

WAVES="${1:-100}"
if ! [[ "$WAVES" =~ ^[0-9]+$ ]] || (( WAVES < 1 )); then
    echo "[run_s7_stability_waves][error] waves must be a positive integer" >&2
    exit 2
fi

mkdir -p reports/quality
ts="$(date +%Y%m%d-%H%M%S)"
report="reports/quality/s7_stability_waves_${ts}.log"
summary="reports/quality/s7_stability_waves_${ts}.summary"

declare -a TEST_SELECTION=(
    "tests/architecture/test_quality_debt_scorecard.py::test_debt_scorecard_current_quarter_within_budget"
    "tests/architecture/test_quality_debt_scorecard.py::test_debt_scorecard_registry_sync_is_valid"
    "tests/architecture/test_diagram_regression_workflow.py::test_docs_workflow_runs_doc_integrity_guardrails"
    "tests/architecture/test_docs_governance_workflow.py::test_docs_workflow_runs_lightweight_docs_governance_profile"
    "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries"
    "tests/architecture/test_p1_config_topology_closeout.py::test_p1_config_topology_surfaces_stay_bounded_and_helper_backed[src/bioetl/infrastructure/config/pipeline_config_loader.py-145-required_modules4]"
)

pass=0
fail=0
echo "waves=$WAVES" | tee -a "$report"
echo "runner=scripts/engineering/dev/run_pytest.sh" | tee -a "$report"

for wave in $(seq 1 "$WAVES"); do
    start="$(date +%s)"
    out_file="/tmp/s7_wave_${wave}_${ts}.out"
    if bash scripts/engineering/dev/run_pytest.sh "${TEST_SELECTION[@]}" --narrow -q --maxfail=1 >"$out_file" 2>&1; then
        status="PASS"
        pass=$((pass + 1))
    else
        status="FAIL"
        fail=$((fail + 1))
    fi
    end="$(date +%s)"
    duration="$((end - start))"
    printf 'wave=%03d status=%s duration_s=%d\n' "$wave" "$status" "$duration" | tee -a "$report"
    if [[ "$status" == "FAIL" ]]; then
        {
            echo "--- wave $wave fail tail ---"
            tail -n 80 "$out_file" || true
            echo "--- end wave $wave ---"
        } >>"$report"
    fi
done

{
    echo "report=$report"
    echo "waves=$WAVES"
    echo "pass=$pass"
    echo "fail=$fail"
} | tee "$summary"

echo "$summary"
