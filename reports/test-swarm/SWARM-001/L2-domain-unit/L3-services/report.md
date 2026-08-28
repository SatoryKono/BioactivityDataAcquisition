# Test Report: tests/unit/domain/services/

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-services
**Agent Level**: L3
**Scope**: tests/unit/domain/services/
**Source**: src/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 50 | 60 | +10 | |
| Passed | 45 | 60 | +15 | |
| Failed | 5 | 0 | -5 | ✅ |
| Coverage | 82.0% | 90.0% | +8.0% | ✅ ≥85% |
| Flaky tests | 1 | 0 | -1 | |
| Median time | 45ms | 40ms | -5ms | |
| p95 time | 200ms | 150ms | -50ms | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_L3-services_1 | State | Bug | Fix | `file:1` |

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | test_reg_L3-services | Bug | test_a.py |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | test_new_L3-services.py | 10 | mod.py | +8.0% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | test_opt_L3-services | 1s | 0.1s | Opt |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | test_flaky_L3-services | 20% | fixed | State |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | None | None | P3 | Requires Manual Review |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/... -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- None
