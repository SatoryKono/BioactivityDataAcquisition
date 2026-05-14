# Test Report: tests/unit/infrastructure/adapters/pubmed

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-adapters-pubmed
**Agent Level**: L3
**Scope**: tests/unit/infrastructure/adapters/pubmed
**Source**: src/bioetl/infrastructure/adapters/pubmed

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 65 | 65 | +0 | |
| Passed | 65 | 65 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 86% | 86% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.1s | 0.1s | -0s | |
| p95 time | 0.5s | 0.5s | -0s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | `tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py::TestSearchByTitle::test_constructs_correct_pubmed_query` | Data | Validation failure | Fixed boundary condition | `src/bioetl/infrastructure/adapters/pubmed/adapter.py:42` |


## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| - | - | - | - |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| - | - | - | - | - |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| - | - | - | - | - |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| - | - | - | - | - |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| - | - | - | - | - |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/infrastructure/adapters/pubmed -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/infrastructure/adapters/pubmed`

## Risks & Requires Manual Review
- None
