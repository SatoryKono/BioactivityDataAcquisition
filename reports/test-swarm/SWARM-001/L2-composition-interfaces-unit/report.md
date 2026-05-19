# Test Report: tests/unit/composition/ + tests/unit/interfaces/

**Дата**: 2026-05-19 11:06
**Agent ID**: L2-composition-interfaces-unit
**Agent Level**: L2
**Scope**: tests/unit/composition/ + tests/unit/interfaces/
**Source**: src/bioetl/composition

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 1378 | 1378 | 0 | |
| Passed | 1377 | 1377 | 0 | |
| Failed | 1 | 1 | 0 | ❌ |
| Coverage | 90% | 90% | 0 | ✅ ≥85% |
| Flaky tests | 1 | 1 | 0 | |
| Median time | 100s | 100s | 0 | |
| p95 time | 300s | 300s | 0 | |

## Fixed Tests
None.

## Existing Failures
- `tests/unit/composition/services/test_versioning.py::test_get_code_revision_provenance_uses_same_windows_git_fallback_for_dirty_check`

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/composition/ + tests/unit/interfaces/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/composition`
