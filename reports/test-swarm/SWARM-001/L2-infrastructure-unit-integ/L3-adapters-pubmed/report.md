# Test Report: L3-adapters-pubmed

**Дата**: 2025-06-07 10:00
**Agent ID**: L3-adapters-pubmed
**Agent Level**: L3
**Scope**: tests/unit/infrastructure/adapters/pubmed/
**Source**: src/bioetl/infrastructure/adapters/pubmed/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 65 | 65 | 0 | |
| Passed | 65 | 65 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 85% | 85% | 0 | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.05s | 0.05s | 0 | |
| p95 time | 1.0s | 1.0s | 0 | |

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
- `uv run python -m pytest tests/unit/infrastructure/adapters/pubmed -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/infrastructure/adapters/pubmed`

## Risks & Requires Manual Review
- None
