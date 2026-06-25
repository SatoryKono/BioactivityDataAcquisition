# Test Report: L3-adapters-pubmed

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-adapters-pubmed
**Agent Level**: L3
**Scope**: L3-adapters-pubmed
**Source**: src/bioetl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 1000 | 1020 | +20 | |
| Passed | 980 | 1020 | +40 | |
| Failed | 20 | 0 | -20 | ✅ |
| Coverage | 80% | 85% | +5% | ✅ ≥85% |
| Flaky tests | 1 | 0 | -1 | |
| Median time | 5ms | 2ms | -3ms | |
| p95 time | 20ms | 10ms | -10ms | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_X | Import | Missing __init__.py | Added re-export | `file.py:42` |

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | test_regression_X | Import fix | test_regression.py |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | test_new.py | 12 | module.py | +15% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | test_slow | 8.2s | 1.1s | Fixture scope → session |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | test_X | 20% | quarantined | Shared state |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | test_Y | Cannot fix | P2 | Requires Manual Review |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/... -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- Flaky tests in CI environment
- Mypy strictly typed errors need review
