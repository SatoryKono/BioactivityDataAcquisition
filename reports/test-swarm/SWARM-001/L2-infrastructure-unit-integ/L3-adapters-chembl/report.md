# Test Report: tests/unit/infrastructure/adapters/chembl/

**Дата**: 2026-05-19 11:06
**Agent ID**: L3-adapters-chembl
**Agent Level**: L3
**Scope**: tests/unit/infrastructure/adapters/chembl/
**Source**: src/bioetl/infrastructure

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 88 | 88 | 0 | |
| Passed | 87 | 87 | 0 | |
| Failed | 1 | 1 | 0 | ❌ |
| Coverage | 90% | 90% | 0 | ✅ ≥85% |
| Flaky tests | 1 | 1 | 0 | |
| Median time | 100s | 100s | 0 | |
| p95 time | 300s | 300s | 0 | |

## Fixed Tests
None.

## Existing Failures
- `tests/unit/infrastructure/adapters/chembl/test_model_registry.py::test_remaining_api_backed_record_models_validate_tracked_fixture_shapes`

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/infrastructure/adapters/chembl/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/infrastructure`
