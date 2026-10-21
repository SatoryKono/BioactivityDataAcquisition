#!/usr/bin/env bash
set -euo pipefail

SIZE_1=1000000
SIZE_2=$((SIZE_1 * 2))
SIZE_5=$((SIZE_1 * 5))

OUT_DIR="reports/performance/raw_logs"
mkdir -p "$OUT_DIR"

{
  echo "=== ENVIRONMENT ==="
  uname -a
  uv run --frozen --no-build python -c "import sys; print(f'Python: {sys.version}')"
  uv run --frozen --no-build python -c "import polars; print(f'Polars: {polars.__version__}')"
  git rev-parse HEAD
} >"$OUT_DIR/env.txt"

echo "=== PREPARING DATA ==="
for size in "$SIZE_1" "$SIZE_2" "$SIZE_5"; do
  uv run --frozen --no-build python scripts/engineering/performance/measure_merge_eager.py prepare "$size"
done

echo ""
echo "=== MEASUREMENTS ==="
for size in "$SIZE_1" "$SIZE_2" "$SIZE_5"; do
  echo "--- Size: ${size} ---"
  parquet="${OUT_DIR}/measure_merge_silver_${size}.parquet"

  echo "EAGER RUN:"
  /usr/bin/time -v uv run --frozen --no-build python scripts/engineering/performance/measure_merge_eager.py eager "$size" >"$OUT_DIR/eager_${size}.txt" 2>&1
  grep -F "EAGER_WALL_TIME:" "$OUT_DIR/eager_${size}.txt"
  grep -F "EAGER_ROWS:" "$OUT_DIR/eager_${size}.txt"
  grep -F "Maximum resident set size" "$OUT_DIR/eager_${size}.txt"

  echo "LAZY RUN:"
  /usr/bin/time -v uv run --frozen --no-build python scripts/engineering/performance/measure_merge_eager.py lazy "$size" >"$OUT_DIR/lazy_${size}.txt" 2>&1
  grep -F "LAZY_WALL_TIME:" "$OUT_DIR/lazy_${size}.txt"
  grep -F "LAZY_ROWS:" "$OUT_DIR/lazy_${size}.txt"
  grep -F "Maximum resident set size" "$OUT_DIR/lazy_${size}.txt"

  echo "HASH CHECK:"
  if uv run --frozen --no-build python scripts/engineering/performance/check_hash.py "$parquet" >"$OUT_DIR/hash_${size}.txt"; then
    cat "$OUT_DIR/hash_${size}.txt"
  else
    status=$?
    cat "$OUT_DIR/hash_${size}.txt"
    exit "$status"
  fi
done

uv run --frozen --no-build python scripts/engineering/performance/generate_report.py
