#!/bin/bash
echo "=== 1. Baseline ==="
uv run python -m pytest tests/ -v --tb=short -q 2>&1 | tail -50 > /tmp/recon_baseline.txt

echo "=== 2. Coverage snapshot ==="
uv run python -m pytest tests/ --cov=src/bioetl --cov-report=term-missing --tb=no -q 2>&1 | tail -80 > /tmp/recon_coverage.txt

echo "=== 3. Failing tests ==="
uv run python -m pytest tests/ -v --tb=line -q 2>&1 | grep "FAILED" | sort > /tmp/recon_failing.txt

echo "=== 4. Architecture tests ==="
uv run python -m pytest tests/architecture/ -v --tb=short -q 2>&1 | tail -30 > /tmp/recon_arch.txt

echo "=== 5. Type check ==="
uv run python -m mypy --strict src/bioetl/ 2>&1 | tail -20 > /tmp/recon_mypy.txt

echo "=== 6. Test categories count ==="
uv run python -m pytest tests/ --collect-only -q 2>&1 | tail -5 > /tmp/recon_categories.txt

echo "=== 7. Top 20 slowest tests ==="
uv run python -m pytest tests/ --durations=20 -q 2>&1 | head -30 > /tmp/recon_slowest.txt
