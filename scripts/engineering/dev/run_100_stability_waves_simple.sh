#!/usr/bin/env bash
set -euo pipefail

WAVES=100
TS="$(date +%Y%m%dT%H%M%S)"
RUN_BASE="stability-simple-$TS"
JUNIT_ROOT="reports/quality/test-runs/junit"

mkdir -p "$JUNIT_ROOT"

for i in $(seq 1 "$WAVES"); do
    WAVE_ID="$(printf "%s-%03d" "$RUN_BASE" "$i")"
    WAVE_DIR="$JUNIT_ROOT/$WAVE_ID"
    mkdir -p "$WAVE_DIR"
    
    echo "Running wave $i..."
    python3 -m pytest \
        tests/architecture/test_config_ci_invariants.py::TestSilverRequiredFieldsCoverage::test_explicit_required_fields_are_covered_by_silver_filters \
        --junitxml="$WAVE_DIR/shard.xml" \
        --no-cov \
        -q > /dev/null 2>&1
done

echo "Aggregating..."
python3 -m scripts.engineering.qa summarize-junit \
    --suite stability-simple \
    --junit-glob "$JUNIT_ROOT/$RUN_BASE-*/*.xml"

echo "Rollup..."
python3 -m scripts.engineering.qa test-health \
    --last 200 \
    --markdown-out reports/quality/test-runs/rollup.md

COUNT=$(grep -m 1 "Runs analyzed:" reports/quality/test-runs/rollup.md | grep -oE "[0-9]+")
echo "Analyzed: $COUNT"
