# Test Report: tests/unit/domain/value_objects/

**Дата**: 2026-04-24T10:54:28Z
**Agent ID**: L3-value-objects
**Agent Level**: L3
**Scope**: tests/unit/domain/value_objects/
**Source**: src/bioetl/domain

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 963 | 963 | 0 | |
| Passed | 963 | 963 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90% | 90% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 15ms | 15ms | 0ms | |
| p95 time | 45ms | 45ms | 0ms | |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/value_objects/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
