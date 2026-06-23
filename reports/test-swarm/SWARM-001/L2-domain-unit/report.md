# Test Report: domain unit

**Дата**: 2026-06-23 10:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 7370 | 7370 | 0 | |
| Passed | 7370 | 7370 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 92% | 92% | 0% | ✅ ≥90% |
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
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain/`

## Risks & Requires Manual Review
None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | tests/unit/domain/schemas/ | DONE | 815 tests, 0 fails |
| 2 | L3-services | tests/unit/domain/services/ | DONE | 679 tests, 0 fails |
| 3 | L3-value-objects | tests/unit/domain/value_objects/ | DONE | 962 tests, 0 fails |
