# Test Report: infrastructure unit and integration

**Дата**: 2026-06-23 10:00
**Agent ID**: L2-infra-unit-integ
**Agent Level**: L2
**Scope**: tests/unit/infrastructure/ + tests/integration/
**Source**: src/bioetl/infrastructure/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 6519 | 6519 | 0 | |
| Passed | 6519 | 6519 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 86% | 86% | 0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.5s | 0.5s | 0s | |
| p95 time | 2.0s | 2.0s | 0s | |

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
- `uv run python -m pytest tests/unit/infrastructure/ tests/integration/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/infrastructure/`

## Risks & Requires Manual Review
None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-adapters-chembl | tests/.../adapters/chembl/ | DONE | 105 tests, 0 fails |
