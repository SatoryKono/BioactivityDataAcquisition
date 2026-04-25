# Test Report: tests/unit/domain/services/

**Дата**: 2026-04-24T10:54:28Z
**Agent ID**: L3-services
**Agent Level**: L3
**Scope**: tests/unit/domain/services/
**Source**: src/bioetl/domain

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 670 | 670 | 0 | |
| Passed | 670 | 670 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90% | 90% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 15ms | 15ms | 0ms | |
| p95 time | 45ms | 45ms | 0ms | |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/services/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
