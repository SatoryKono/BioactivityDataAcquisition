# Test Report: tests/unit/application/pipelines/pubmed/

**Дата**: 2026-04-24T10:54:28Z
**Agent ID**: L3-pipelines-pubmed
**Agent Level**: L3
**Scope**: tests/unit/application/pipelines/pubmed/
**Source**: src/bioetl/application

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 307 | 307 | 0 | |
| Passed | 307 | 307 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90% | 90% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 15ms | 15ms | 0ms | |
| p95 time | 45ms | 45ms | 0ms | |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/application/pipelines/pubmed/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
