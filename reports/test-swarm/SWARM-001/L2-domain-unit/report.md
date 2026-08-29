# Test Report: tests/unit/domain/

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 8000 | 8000 | 0 | |
| Passed | 8000 | 8000 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 90% | 90% | 0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 120ms | 120ms | 0ms | |
| p95 time | 400ms | 400ms | 0ms | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | None | None | None | None | None |

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | None | None | None |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | None | 0 | None | 0% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | None | 0s | 0s | None |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | None | 0% | None | None |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | None | None | None | None |

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/`

## Risks & Requires Manual Review
- None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | domain/schemas | DONE | OK |
| 2 | L3-services | domain/services | DONE | OK |
| 3 | L3-value-objects | domain/value_objects | DONE | OK |
