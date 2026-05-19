# Test Report: tests/unit/infrastructure/adapters/pubmed/

**Дата**: 2026-05-19 11:06
**Agent ID**: L3-adapters-pubmed
**Agent Level**: L3
**Scope**: tests/unit/infrastructure/adapters/pubmed/
**Source**: src/bioetl/infrastructure

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 65 | 65 | 0 | |
| Passed | 65 | 65 | 0 | |
| Failed | 0 | 0 | 0 | ❌ |
| Coverage | 90% | 90% | 0 | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 100s | 100s | 0 | |
| p95 time | 300s | 300s | 0 | |

## Fixed Tests
None.

## Existing Failures

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/infrastructure/adapters/pubmed/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/infrastructure`
