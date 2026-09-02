# Test Report: L2-domain-unit

**Дата**: 2026-08-31 09:41
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 192 | 192 | +0 | |
| Passed | 192 | 192 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 94% | 94% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.01s | 0.01s | -0s | |
| p95 time | 0.05s | 0.05s | -0s | |

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
- `uv run python -m pytest tests/unit/domain/`
- `uv run python -m mypy --strict src/bioetl/domain/`

## Risks & Requires Manual Review
- None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | tests/unit/domain/schemas/ | DONE | Passed |
| 2 | L3-services | tests/unit/domain/services/ | DONE | Passed |
| 3 | L3-value-objects | tests/unit/domain/value_objects/ | DONE | Passed |
