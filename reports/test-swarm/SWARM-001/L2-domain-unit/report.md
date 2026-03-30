# Test Report: L2-domain-unit

**Дата**: 2026-03-05 12:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 100 | 100 | 0 | |
| Passed | 100 | 100 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90.1% | 90.1% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.01s | 0.01s | 0s | |
| p95 time | 0.05s | 0.05s | 0s | |

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

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain/`

## Risks & Requires Manual Review
- None

## L3 Agents (если оркестратор)
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | tests/unit/domain/schemas/ | DONE | All tests pass, 0 fixes |
| 2 | L3-services | tests/unit/domain/services/ | DONE | All tests pass, 0 fixes |
| 3 | L3-value-objects | tests/unit/domain/value_objects/ | DONE | All tests pass, 0 fixes |
