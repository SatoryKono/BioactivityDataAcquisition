# Test Report: L3-pipelines-chembl

**Дата**: 2025-06-07 10:00
**Agent ID**: L3-pipelines-chembl
**Agent Level**: L3
**Scope**: tests/unit/application/pipelines/chembl/
**Source**: src/bioetl/application/pipelines/chembl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 94 | 94 | 0 | |
| Passed | 94 | 94 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 86% | 86% | 0 | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.01s | 0.01s | 0 | |
| p95 time | 0.1s | 0.1s | 0 | |

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

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/application/pipelines/chembl -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/application/pipelines/chembl`

## Risks & Requires Manual Review
- None
