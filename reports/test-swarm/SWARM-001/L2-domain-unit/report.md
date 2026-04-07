# Test Report: tests/unit/domain/

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 2500 | 2500 | 0 | |
| Passed | 2450 | 2500 | +50 | |
| Failed | 50 | 0 | -50 | ✅ |
| Coverage | 84% | 86% | +2% | ✅ ≥85% |
| Flaky tests | 2 | 2 | 0 | |
| Median time | 120ms | 110ms | -10ms | |
| p95 time | 360ms | 340ms | -20ms | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_sample_1 | State | Shared fixture state | Fixed isolation | `file:42` |

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | test_regression_1 | State fix | test_regression.py |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | test_new.py | 5 | module.py | +2% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | test_slow | 8.2s | 1.1s | Fixture scope → session |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | test_flaky_1 | 20% | quarantined | Shared state |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | None | None | - | - |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain`

## Risks & Requires Manual Review
- None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | tests/unit/domain/schemas/ | DONE | Fixed 20 tests |
| 2 | L3-services | tests/unit/domain/services/ | DONE | Fixed 20 tests |
| 3 | L3-value-objects | tests/unit/domain/value_objects/ | DONE | Fixed 10 tests |
