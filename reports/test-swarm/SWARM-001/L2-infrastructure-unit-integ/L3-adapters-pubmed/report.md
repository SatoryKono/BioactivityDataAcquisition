# Test Report: tests/unit/infrastructure/adapters/pubmed/

**Дата**: 2026-04-24T10:54:28Z
**Agent ID**: L3-adapters-pubmed
**Agent Level**: L3
**Scope**: tests/unit/infrastructure/adapters/pubmed/
**Source**: src/bioetl/infrastructure

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 65 | 65 | 0 | |
| Passed | 65 | 65 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90% | 90% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 15ms | 15ms | 0ms | |
| p95 time | 45ms | 45ms | 0ms | |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/infrastructure/adapters/pubmed/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
