#!/bin/bash
set -e

# Data sizes
SIZE_1=1000000
SIZE_2=$((SIZE_1 * 2))
SIZE_5=$((SIZE_1 * 5))

OUT_DIR="reports/performance/raw_logs"
mkdir -p "$OUT_DIR"

echo "=== ENVIRONMENT ===" > "$OUT_DIR/env.txt"
uname -a >> "$OUT_DIR/env.txt"
uv run --no-build python -c "import sys; print(f'Python: {sys.version}')" >> "$OUT_DIR/env.txt"
uv run --no-build python -c "import polars; print(f'Polars: {polars.__version__}')" >> "$OUT_DIR/env.txt"
git rev-parse HEAD >> "$OUT_DIR/env.txt"

echo "=== PREPARING DATA ==="
uv run --no-build python scripts/engineering/performance/measure_merge_eager.py prepare $SIZE_1
uv run --no-build python scripts/engineering/performance/measure_merge_eager.py prepare $SIZE_2
uv run --no-build python scripts/engineering/performance/measure_merge_eager.py prepare $SIZE_5

echo ""
echo "=== MEASUREMENTS ==="
for size in $SIZE_1 $SIZE_2 $SIZE_5; do
    echo "--- Size: $size ---"

    echo "EAGER RUN:"
    /usr/bin/time -v uv run --no-build python scripts/engineering/performance/measure_merge_eager.py eager $size > "$OUT_DIR/eager_${size}.txt" 2>&1
    cat "$OUT_DIR/eager_${size}.txt" | grep -E "EAGER|Maximum resident set size"

    echo "LAZY RUN:"
    /usr/bin/time -v uv run --no-build python scripts/engineering/performance/measure_merge_eager.py lazy $size > "$OUT_DIR/lazy_${size}.txt" 2>&1
    cat "$OUT_DIR/lazy_${size}.txt" | grep -E "LAZY|Maximum resident set size"

    echo "HASH CHECK:"
    uv run --no-build python scripts/engineering/performance/check_hash.py "reports/performance/raw_logs/measure_merge_silver_${size}.parquet" > "$OUT_DIR/hash_${size}.txt"
    cat "$OUT_DIR/hash_${size}.txt"
done
