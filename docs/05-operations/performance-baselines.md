______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-25'

______________________________________________________________________

# Performance Baselines

*Reference: [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md), [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Baselines are measured for local execution path.

This document defines performance baselines for critical operations in BioETL.
These baselines are enforced by benchmark tests in `tests/benchmarks/`.

Hotspot regression budgets (relative thresholds for CI stability) are enforced by:

- `tests/performance/test_hotspot_budgets.py`
- `tests/performance/hotspot_budgets.json`
- `scripts/engineering/qa/generate_hotspot_degradation_report.py` (`uv run python -m scripts.engineering.qa report-hotspots`, rolling-window degradation report)

## Overview

Performance baselines ensure that:

1. Critical operations meet expected throughput requirements
1. Latency stays within acceptable bounds
1. Performance regressions are detected early

## Baseline Metrics

### Content Hash Generation

| Record Size         | Target Latency | Throughput       |
| ------------------- | -------------- | ---------------- |
| Small (~10 fields)  | < 50 µs        | > 20,000 ops/sec |
| Medium (~50 fields) | < 150 µs       | > 6,500 ops/sec  |
| Large (~100 fields) | < 500 µs       | > 2,000 ops/sec  |

### Batch Processing

| Batch Size    | Target Latency | Throughput        |
| ------------- | -------------- | ----------------- |
| 100 records   | < 10 ms        | > 100 batches/sec |
| 1000 records  | < 100 ms       | > 10 batches/sec  |
| 10000 records | < 1 sec        | > 1 batch/sec     |

### JSON Serialization

| Operation                  | Target Latency |
| -------------------------- | -------------- |
| Canonical JSON (50 fields) | < 100 µs       |

### DataFrame Operations (Polars)

| Operation          | Records | Target Latency |
| ------------------ | ------- | -------------- |
| DataFrame creation | 5000    | < 20 ms        |
| Filter operation   | 5000    | < 5 ms         |
| Group + Aggregate  | 5000    | < 10 ms        |

## Measurement Methodology

`tests/benchmarks/` cases that use the `benchmark` fixture are measured with
`pytest-benchmark` only when that plugin is explicitly enabled. Default
`addopts` keeps `-p no:benchmark`, so a normal pytest run skips those cases.
The dispatch-only Performance Nightly workflow is the shipped CI caller that
passes `-p tests.benchmarks.benchmark_vcs_guard` before `-p benchmark` and
writes `reports/performance/benchmark-measurements.json`. The local caller is
`make test-benchmark`: it creates that directory, labels the run
`BIOETL_BENCHMARK_CALLER=local-makefile` with dataset
`bioetl-synthetic-benchmarks-v1`, and loads the same guard before
`-p benchmark`. The local `run_pytest.sh` and `run_pytest.ps1` wrappers
prepend that same guard before `-p benchmark` when the selection is a
benchmark path, a benchmark marker, or an explicit `-p` / `--plugins`
benchmark request, including `BIOETL_PYTEST_AUTOLOAD=1`. That guard blocks
the plugin's git/hg probes and records the checkout HEAD from the gitdir.
`dirty_state` stays `unknown`. The run id is not a commit SHA. Hotspot
reporting and gating run after failures, except cancellation, and reject missing
or incomplete observations. Artifact upload rejects missing files.

Measurement settings when the plugin is on:

- Minimum 5 rounds per test
- Statistical outlier detection
- Manual `workflow_dispatch` on Ubuntu Latest (not a per-PR required check)

## Running Benchmarks

```bash
make test-benchmark

# Explicit local caller. Guard first, then -p benchmark.
mkdir -p reports/performance
BIOETL_BENCHMARK_CALLER=local \
BIOETL_BENCHMARK_DATASET=bioetl-synthetic-benchmarks-v1 \
pytest tests/benchmarks/ \
  -m benchmark \
  -p tests.benchmarks.benchmark_vcs_guard \
  -p benchmark \
  -p no:xdist \
  --benchmark-json=reports/performance/benchmark-measurements.json

python -m tests.benchmarks.benchmark_vcs_guard \
  --validate-measurement-json reports/performance/benchmark-measurements.json

# Run blocking hotspot regression budgets (relative thresholds)
pytest tests/performance/test_hotspot_budgets.py -m "benchmark and performance" -p no:xdist

# Collect observations and recalibrate baselines
pytest tests/performance/test_hotspot_budgets.py \
  -m "benchmark and performance" \
  -p no:xdist \
  --perf-obs-out /tmp/hotspot-observations.jsonl
uv run python -m scripts.engineering.qa calibrate-hotspots \
  --observations /tmp/hotspot-observations.jsonl \
  --budgets tests/performance/hotspot_budgets.json \
  --latency-q 1.0 \
  --throughput-q 0.0

# Build rolling-window degradation report (for CI summary/artifacts)
uv run python -m scripts.engineering.qa report-hotspots \
  --observations /tmp/hotspot-observations.jsonl \
  --budgets tests/performance/hotspot_budgets.json \
  --window-size 5 \
  --json-out /tmp/hotspot-degradation.json \
  --markdown-out /tmp/hotspot-degradation.md
```

## Measurement acceptance for #12044

`reports/performance/benchmark-measurements.json` is an input candidate for
#12044, not a regression verdict. One recorded round only proves that the
selected benchmark case executed. It does not prove that performance stayed
inside a budget.

#12044 can accept the file only when
`python -m tests.benchmarks.benchmark_vcs_guard --validate-measurement-json`
exits 0. That check requires all of the following:

- `benchmarks` is a non-empty list and every `stats.rounds` is an integer >= 1;
  a JSON boolean is not an integer
- `bioetl_source.schema_version` is the integer 1
- `bioetl_source.revision` is the 40-hex gitdir HEAD of the tree being
  validated, with `revision_method` `gitdir_head_file`
- `bioetl_source.dirty_state` is `unknown`; a missing dirty probe is not a
  clean tree
- `commit_info.id` equals that revision and `commit_info.dirty` is null
- `bioetl_run.id` is a UUID and is not the source revision
- `bioetl_run.kind` is `pytest-benchmark` and `bioetl_run.caller` names the
  run rather than a commit; `unspecified` is rejected
- `bioetl_vcs_guard.installed_before_plugin` is true and
  `blocked_probe_attempts` is 0

A blocked or unreadable HEAD stays `unknown` and fails this check. The nightly
caller supplies `bioetl_measurement.dataset` as
`bioetl-synthetic-benchmarks-v1`; the guard records `github-actions` only when
`GITHUB_ACTIONS=true`, otherwise `local`. The reducer separately checks run
identity and context before producing an evidence candidate. Local measurements
do not establish GitHub Actions provenance or adopt a baseline.

## Updating Baselines

When performance improvements are made:

1. Run benchmarks to verify improvement
1. Update baseline values in this document
1. Update threshold assertions in tests
1. Save new benchmark baseline file

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- Architecture Review Report (R5)
