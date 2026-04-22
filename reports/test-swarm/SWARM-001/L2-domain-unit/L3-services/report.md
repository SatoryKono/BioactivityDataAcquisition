# Test Report: tests/unit/domain/services/

**Дата**: 2026-04-22 09:55
**Agent ID**: L3-services
**Agent Level**: L3
**Scope**: tests/unit/domain/services/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 3224 | 3224 | +0 | |
| Passed | 3224 | 3224 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 92% | 92% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.1s | 0.1s | -0.0s | |
| p95 time | 0.4s | 0.4s | -0.0s | |

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
- `uv run python -m pytest tests/unit/domain/services/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain/`

## Risks & Requires Manual Review
- None
