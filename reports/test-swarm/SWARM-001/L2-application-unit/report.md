# Test Report: tests/unit/application/

**Дата**: 2026-04-02 09:10
**Agent ID**: L2-application-unit
**Agent Level**: L2
**Scope**: tests/unit/application/
**Source**: src/bioetl/application/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 4465 | 4465 | 0 | |
| Passed | 4465 | 4465 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 86.5% | 86.5% | 0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 15s | 13s | -2s | |
| p95 time | 150s | 130s | -20s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| - | - | - | - | - | - |

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
| 1 | test_base_pipeline | 8.2s | 1.1s | Fixture scope → session |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| - | - | - | - | - |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| - | - | - | - | - |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/application/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/application/`

## Risks & Requires Manual Review
- None
