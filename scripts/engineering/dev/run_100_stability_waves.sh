#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

WAVES=100
TS="$(date +%Y%m%dT%H%M%S)"
RUN_BASE="stability-100-$TS"
JUNIT_ROOT="reports/quality/test-runs/junit"

echo "[stability] Starting $WAVES waves of tests..."

for i in $(seq 1 "$WAVES"); do
    WAVE_ID="$(printf "%s-%03d" "$RUN_BASE" "$i")"
    WAVE_DIR="$JUNIT_ROOT/$WAVE_ID"
    
    echo "[wave $i/100] run_id=$WAVE_ID"
    
    # Прямой запуск pytest для максимальной скорости (без sharded обертки)
    python3 -m pytest \
        tests/architecture/test_config_ci_invariants.py::TestSilverRequiredFieldsCoverage::test_explicit_required_fields_are_covered_by_silver_filters \
        --junitxml="$WAVE_DIR/shard.xml" \
        --no-cov \
        -q \
        > /dev/null 2>&1 || true
done

echo "[stability] All $WAVES waves finished."

# Агрегируем результаты
echo "[stability] Aggregating results into test-health..."
python3 -m scripts.engineering.qa summarize-junit \
    --suite stability-100 \
    --junit-glob "$JUNIT_ROOT/$RUN_BASE-*/*.xml"

# Генерируем финальный rollup
echo "[stability] Generating rollup.md..."
python3 -m scripts.engineering.qa test-health \
    --last 200 \
    --markdown-out reports/quality/test-runs/rollup.md

# Проверка количества запусков в rollup.md (простейший grep по тексту)
# "Runs analyzed: 123"
COUNT=$(grep -m 1 "Runs analyzed:" reports/quality/test-runs/rollup.md | grep -oE "[0-9]+")
echo "[stability] Runs analyzed in rollup: $COUNT"

if [ "$COUNT" -lt 100 ]; then
    echo "[stability] ERROR: Only $COUNT runs collected. Expected at least 100."
    exit 1
fi

echo "[stability] SUCCESS: 100 runs analyzed."
