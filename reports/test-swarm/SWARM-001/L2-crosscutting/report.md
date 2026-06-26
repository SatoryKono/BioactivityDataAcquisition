# Test Report: tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-crosscutting
**Agent Level**: L2
**Scope**: tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/
**Source**: src/bioetl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 1594 | 1594 | +0 | |
| Passed | 1594 | 1594 | +0 | |
| Failed | 0 | 1 | +1 | ❌ |
| Coverage | 86% | 86% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.05s | 0.05s | -0.0s | |
| p95 time | 0.2s | 0.2s | -0.0s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|


## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|


## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|


## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|


## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|


## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | test_inventory_doc_tables_match_yaml_registry | Data mismatch | P2 | Requires Manual Review |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/... -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- Dependency on external service in test_Y
