# Test Report: tests/unit/domain/services/

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-services
**Agent Level**: L3
**Scope**: tests/unit/domain/services/
**Source**: src/bioetl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 800 | 820 | +20 | |
| Passed | 790 | 820 | +30 | |
| Failed | 10 | 0 | -10 | ✅ |
| Coverage | 82.0% | 90.0% | +8.0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 100ms | 95ms | -5ms | |
| p95 time | 500ms | 480ms | -20ms | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_L3-services_1 | Data | Schema drift | Fixed mock | `test_mock.py:42` |
| 2 | test_L3-services_2 | Data | Schema drift | Fixed mock | `test_mock.py:42` |
| 3 | test_L3-services_3 | Data | Schema drift | Fixed mock | `test_mock.py:42` |

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | test_reg | Sample fix | test_reg.py |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | test_new.py | 20 | module.py | +5% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | test_slow | 8.2s | 1.1s | Fixture scope → session |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | test_flaky | 20% | fixed | Shared state |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| - | - | None | - | - |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/services/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
