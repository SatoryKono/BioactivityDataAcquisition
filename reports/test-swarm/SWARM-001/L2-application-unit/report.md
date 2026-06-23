# Test Report: application unit

**Дата**: 2026-06-23 10:00
**Agent ID**: L2-app-unit
**Agent Level**: L2
**Scope**: tests/unit/application/
**Source**: src/bioetl/application/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 5347 | 5347 | 0 | |
| Passed | 5347 | 5347 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 87% | 87% | 0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.05s | 0.05s | 0s | |
| p95 time | 0.1s | 0.1s | 0s | |

## Fixed Tests
None

## Regression Tests Added (for fixed bugs)
None

## New Tests Created
None

## Optimized Tests
None

## Flaky Tests Detected
None

## Remaining Issues
None

## Evidence
- `uv run python -m pytest tests/unit/application/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/application/`

## Risks & Requires Manual Review
None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-pipelines-chembl | tests/unit/application/pipelines/chembl/ | DONE | 94 tests, 0 fails |
| 2 | L3-pipelines-pubmed | tests/unit/application/pipelines/pubmed/ | DONE | 308 tests, 0 fails |
