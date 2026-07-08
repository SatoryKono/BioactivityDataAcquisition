______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Test Execution Optimization Guide

## Overview

This guide describes the current, repository-accurate approach to optimizing test execution in BioETL.

The main goal is not "maximum parallelism at any cost", but fast feedback with stable and reproducible runs:

- local default remains serial for stability;
- parallelism is enabled explicitly for safe subsets;
- `serial` tests are isolated into their own pass;
- coverage and architecture gates are kept explicit rather than hidden inside generic shortcuts.

## Current Test Execution Model

BioETL already has a test optimization strategy in place:

- local default pytest configuration is serial;
- fast local feedback uses `xdist` only for `not serial` tests;
- CI uses parallel shards plus a dedicated serial coverage pass;
- benchmark and slow tests are excluded from standard runs by default;
- Hypothesis uses dedicated profiles for local-fast and CI execution.

The canonical source of truth is:

- `Makefile` for local entrypoints;
- `pyproject.toml` for pytest markers, defaults, and plugin config;
- `.github/workflows/tests.yml` for CI orchestration.

## Canonical Commands

### Local Stable Default

Use this when you want the safest full local run:

```bash
make test
```

Direct equivalent:

```bash
uv run pytest tests/ -p no:xdist -m "not e2e" --cov=src/bioetl --cov-report=term-missing --cov-fail-under=85
```

### Fast Feedback

Use this for the quickest day-to-day signal:

```bash
make test-fast
```

Direct equivalent:

```bash
HYPOTHESIS_PROFILE=fast \
uv run pytest tests/unit/ tests/architecture/ \
  -n auto --dist loadscope --max-worker-restart=0 \
  -m "not slow and not serial" \
  --timeout=15 \
  --ignore=tests/benchmarks
```

### Fast Stable Coverage

Use this when you want a faster local coverage pass without mixing serial and parallel-safe tests:

```bash
make test-cov-fast-stable
```

This target runs in two phases:

1. parallel pass for `not serial and not e2e and not benchmark and not slow`;
1. serial pass for `serial and not e2e and not benchmark and not slow`;
1. coverage combine and threshold enforcement.

Notes:

- this target ignores `tests/architecture` by default for speed;
- set `INCLUDE_ARCH_GATES=1` to add architecture checks;
- local fast coverage defaults to `LOCAL_COV_FAIL_UNDER=80`.

Example:

```bash
INCLUDE_ARCH_GATES=1 LOCAL_COV_FAIL_UNDER=85 make test-cov-fast-stable
```

### CI-Like Local Run

Use this when reproducing CI behavior locally:

```bash
make test-ci-local
```

Direct equivalent:

```bash
HYPOTHESIS_PROFILE=ci \
uv run pytest tests/ \
  -m "not e2e and not serial" \
  -n auto --dist loadscope --max-worker-restart=0 \
  --cov=src/bioetl --cov-fail-under=85
```

### Profiling Slow Tests

Use this to collect a current baseline before proposing changes:

```bash
make test-profile
```

Or:

```bash
uv run pytest tests/ -q --durations=50 --durations-min=0.1 --ignore=tests/e2e/ --ignore=tests/benchmarks/
```

## Windows and PowerShell Notes

On Windows, `make` may not be available. Use direct `uv run ...` commands instead.

PowerShell example for the fast stable coverage flow:

```powershell
& {
    $env:UV_CACHE_DIR = "$env:TEMP\.uv-cache"

    New-Item -ItemType Directory -Force "reports\coverage" | Out-Null
    Remove-Item "reports\coverage\.coverage.parallel","reports\coverage\.coverage.serial","reports\coverage\.coverage" -Force -ErrorAction SilentlyContinue

    $env:COVERAGE_FILE = "reports/coverage/.coverage.parallel"
    uv run pytest tests/ -m "not serial and not e2e and not benchmark and not slow" --ignore=tests/architecture -n 4 --dist loadscope --max-worker-restart=0 --cov=src/bioetl --cov-report=

    $env:COVERAGE_FILE = "reports/coverage/.coverage.serial"
    uv run pytest tests/ -m "serial and not e2e and not benchmark and not slow" --ignore=tests/architecture -p no:xdist --cov=src/bioetl --cov-report=

    $env:COVERAGE_FILE = "reports/coverage/.coverage"
    uv run coverage combine --keep reports/coverage
    uv run coverage report --show-missing --fail-under=80
}
```

`--keep` avoids Windows file-lock cleanup failures (`WinError 32`) during combine.

## Stable Parallelism Strategy

### Why We Do Not Parallelize Everything

The repository intentionally does not treat "enable `-n auto` everywhere" as a universal optimization.

Some tests:

- rely on shared state;
- are sensitive to worker restarts;
- interact poorly with benchmark plugins;
- become harder to debug when mixed with unrelated failures.

Because of that, BioETL uses the following rules:

- mark non-parallel-safe tests with `@pytest.mark.serial`;
- run only `not serial` tests under `xdist`;
- use `--dist loadscope` to keep related tests grouped more safely;
- use `--max-worker-restart=0` to avoid hidden instability loops;
- keep benchmark runs on `-p no:xdist`.

### Recommended Marker Split

Fast parallel-safe subset:

```bash
uv run pytest tests/ -m "not slow and not serial"
```

Serial-only subset:

```bash
uv run pytest tests/ -m "serial and not e2e and not benchmark" -p no:xdist
```

Benchmark-only subset:

```bash
uv run pytest tests/performance/ -m "benchmark and performance" -p no:xdist
```

## Practical Optimization Opportunities

### 1. Reduce the `serial` Surface Area

The highest-value optimization is usually not "more workers", but "fewer tests that require serial execution".

Before changing worker counts:

- audit why a test is marked `serial`;
- remove the marker only after proving isolation;
- prefer fixture-level isolation over global locks or shared resources.

### 2. Optimize Fixture Scope Carefully

Module-scoped fixtures can help when object construction is expensive and the fixture is immutable.

Example:

```python
import pytest


@pytest.fixture(scope="module")
def validator():
    return AggregationValidator()
```

Do not widen scope if the fixture mutates state between tests.

### 3. Use Better Focused Runs

For faster inner loops, prefer markers and narrow paths over broad full-suite runs:

```bash
uv run pytest tests/unit/domain/ -q
uv run pytest tests/unit/domain/behavior/ -k "cross_validation or aggregation"
uv run pytest tests/architecture/ -q --tb=short
uv run pytest tests/ -p no:xdist --lf
```

### 4. Parameterize Repetitive Tests

Prefer parameterization when multiple tests differ only in data:

```python
import pytest


@pytest.mark.parametrize(
    "config_variant",
    [
        "valid_config_1",
        "valid_config_2",
        "edge_case_config",
    ],
)
def test_validate_config_variants(validator, config_variant):
    config = load_config(config_variant)
    result = validator.validate_aggregation_config(config)
    assert result.is_valid()
```

### 5. Cache Expensive Test Data Correctly

If pytest cache is useful, use the real fixture API:

```python
import pytest


@pytest.fixture
def cached_test_data(request, cache):
    cache_key = f"expensive-data/{request.node.name}"
    data = cache.get(cache_key, None)
    if data is None:
        data = generate_expensive_test_data()
        cache.set(cache_key, data)
    return data
```

Use this only for deterministic, serialization-friendly data.

### 6. Tune Hypothesis for the Run Mode

BioETL already uses Hypothesis profiles as part of optimization:

- `HYPOTHESIS_PROFILE=fast` for quick local feedback;
- `HYPOTHESIS_PROFILE=ci` for CI runs.

Do not hard-code aggressive per-test reductions unless the test remains meaningful.

## Benchmark and Performance Budget Guidance

Benchmark execution is a dedicated workflow, not part of the default test path.

Use:

```bash
uv run pytest tests/performance/ -m "benchmark and performance" -p no:xdist
```

Guidelines:

- do not mix benchmark conclusions with ordinary unit-test timings;
- do not present one narrow subsystem benchmark as a repo-wide baseline;
- keep performance budgets tied to concrete hotspots;
- compare like with like: same command, same marker set, same environment.

## CI Reality

CI already includes several optimizations:

- fast parallel lane for unit and architecture tests;
- matrix sharding across test groups;
- pytest cache fingerprinting;
- dedicated serial coverage verification pass;
- resilient runner logic for sensitive flows.

The shared `.github/actions/setup-python-uv` action keeps environment cache
reuse deterministic by hashing the environment-shaping inputs separately from
test-result cache inputs. The uv/virtualenv cache is invalidated by changes to
`uv.lock`, `pyproject.toml`, `.github/actions/setup-python-uv/action.yml`,
`uv-extras`, `uv-sync-args`, or the Python version. The pytest cache remains a
separate lane-specific cache controlled by `pytest-cache-fingerprint`; do not
fold pytest cache inputs into the uv environment cache key.

Because of that, the next optimization pass should focus on:

1. reducing unstable or unnecessarily serial tests;
1. shrinking slow fixture setup;
1. improving targeted local developer loops;
1. keeping CI cache keys and shard balance healthy.

Do not replace the real CI with generic sample YAML. If the workflow changes, update `.github/workflows/tests.yml` and this guide together.

## Measurement Rules

When proposing a new optimization, always record:

- exact command;
- date;
- platform and Python version;
- whether the run was serial or parallel;
- whether coverage was enabled;
- whether architecture tests were included;
- whether Hypothesis profile was `fast`, `ci`, or default.

Good example:

```text
2026-03-26
Command: make test-cov-fast-stable
Platform: Windows 11 / PowerShell
Python: 3.13
Coverage: enabled
Architecture tests: excluded
Hypothesis profile: default
```

Without this metadata, timing comparisons are easy to misread.

## 2026-07-08 TST Corrections

The current test-performance plan is measurement-first. Claims such as
"40-60% faster" are not accepted from structure alone; they require a dated
before/after baseline in `reports/test-telemetry/` using the same lane, marker
expression, coverage mode, worker count, platform, Python version, and Hypothesis
profile.

The latest committed slow-test evidence points first at architecture governance
scans, so optimization work should start with cached scans, shard boundaries,
and artifact freshness checks before changing E2E or VCR execution. `xdist`
remains limited to the explicit parallel-safe lanes in
`configs/quality/test_matrix.yaml`; local pytest defaults stay serial, and VCR,
memory, benchmark, and stateful integration lanes remain serial or bounded until
their lane definitions prove otherwise.

Storage test optimization must use named test seams such as
`tests/fakes/storage_fake.py` or `tmp_path`-backed storage instances. Do not
replace the plan with a generic "in-memory Delta" item unless the measured
backend is actually Delta-compatible and the filesystem-specific integration
coverage remains intact.

VCR maintenance is freshness/pruning governance, not mass consolidation. The
blocking surfaces are metadata sidecars, stale-age checks, catalog drift, and
replay safety. Golden-test expansion is likewise bounded: Gold DQ bundle
snapshots cover the explicit DQ-sensitive registry, not every Gold entity by
default.

## Updated Optimization Plan

### Phase 1: Keep the Current Flow Accurate

- treat `Makefile`, `pyproject.toml`, and `tests.yml` as the canonical contract;
- avoid stale hard-coded timing tables;
- document PowerShell and `uv run` variants alongside `make`.

### Phase 2: Improve Developer Feedback Loops

- prefer `make test-fast` and `make test-profile` for day-to-day work;
- use `--lf`, narrow paths, and `-k` filters more aggressively;
- separate benchmark discussions from ordinary test feedback.

### Phase 3: Reduce Stability Friction

- investigate tests that still require `serial`;
- fix shared-state leaks instead of increasing worker count blindly;
- keep `--dist loadscope` and `--max-worker-restart=0` unless evidence shows a better default.

### Phase 4: Strengthen Measurement Discipline

- collect dated before/after measurements for any optimization proposal;
- compare the same marker set and the same coverage mode;
- update this guide only after the workflow is actually implemented.

## Success Criteria

The optimization effort is successful when:

- developers can choose the right command without guessing;
- local fast runs are fast and reproducible;
- CI remains stable under `xdist`;
- coverage thresholds stay explicit;
- documentation matches the real repository behavior.

## Conclusion

BioETL does not need a generic "turn on parallel pytest" guide. It needs a stable, repository-specific execution model, and that model already exists.

The next wave of optimization should therefore focus on improving isolation, reducing unnecessary serial tests, and tightening measurement quality rather than rewriting the test strategy from scratch.
