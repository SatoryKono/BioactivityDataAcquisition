# Performance Baselines

*Reference: [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Baselines are measured for local execution path.

This document defines performance baselines for critical operations in BioETL.
These baselines are enforced by benchmark tests in `tests/benchmarks/`.

Hotspot regression budgets (relative thresholds for CI stability) are enforced by:
- `tests/performance/test_hotspot_budgets.py`
- `tests/performance/hotspot_budgets.json`

## Overview

Performance baselines ensure that:
1. Critical operations meet expected throughput requirements
2. Latency stays within acceptable bounds
3. Performance regressions are detected early

## Baseline Metrics

### Content Hash Generation

| Record Size | Target Latency | Throughput |
|-------------|----------------|------------|
| Small (~10 fields) | < 50 µs | > 20,000 ops/sec |
| Medium (~50 fields) | < 150 µs | > 6,500 ops/sec |
| Large (~100 fields) | < 500 µs | > 2,000 ops/sec |

### Batch Processing

| Batch Size | Target Latency | Throughput |
|------------|----------------|------------|
| 100 records | < 10 ms | > 100 batches/sec |
| 1000 records | < 100 ms | > 10 batches/sec |
| 10000 records | < 1 sec | > 1 batch/sec |

### JSON Serialization

| Operation | Target Latency |
|-----------|----------------|
| Canonical JSON (50 fields) | < 100 µs |

### DataFrame Operations (Polars)

| Operation | Records | Target Latency |
|-----------|---------|----------------|
| DataFrame creation | 5000 | < 20 ms |
| Filter operation | 5000 | < 5 ms |
| Group + Aggregate | 5000 | < 10 ms |

## Measurement Methodology

Baselines are measured using `pytest-benchmark` with:
- Minimum 5 rounds per test
- Statistical outlier detection
- CI environment: Ubuntu Latest, Python 3.11

## Running Benchmarks

```bash
# Run all benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare against saved baseline
pytest tests/benchmarks/ --benchmark-compare

# Save new baseline
pytest tests/benchmarks/ --benchmark-save=baseline

# Generate JSON report
pytest tests/benchmarks/ --benchmark-json=benchmark.json

# Run blocking hotspot regression budgets (relative thresholds)
pytest tests/performance/test_hotspot_budgets.py -m "benchmark and performance" -p no:xdist

# Collect observations and recalibrate baselines
pytest tests/performance/test_hotspot_budgets.py \
  -m "benchmark and performance" \
  -p no:xdist \
  --perf-obs-out /tmp/hotspot-observations.jsonl
python scripts/calibrate_hotspot_budgets.py \
  --observations /tmp/hotspot-observations.jsonl \
  --budgets tests/performance/hotspot_budgets.json \
  --latency-q 1.0 \
  --throughput-q 0.0
```

## Updating Baselines

When performance improvements are made:

1. Run benchmarks to verify improvement
2. Update baseline values in this document
3. Update threshold assertions in tests
4. Save new benchmark baseline file

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- Architecture Review Report (R5)
