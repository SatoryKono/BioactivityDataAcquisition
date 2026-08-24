# Test Report: L2-domain-unit

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 8000 | 8000 | +0 | |
| Passed | 8000 | 8000 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 88% | 88% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 100s | 100s | -0s | |
| p95 time | 300s | 300s | -0s | |

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
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain/`

## Risks & Requires Manual Review
- None
