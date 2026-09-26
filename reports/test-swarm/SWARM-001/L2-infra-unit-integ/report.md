# Test Report: L2-infra-unit-integ

**Дата**: 2026-08-31 09:41
**Agent ID**: L2-infra-unit-integ
**Agent Level**: L2
**Scope**: tests/unit/infrastructure/ tests/integration/
**Source**: src/bioetl/infrastructure/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 140 | 140 | +0 | |
| Passed | 140 | 140 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 86% | 86% | +0% | ✅ ≥85% |
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
- `uv run python -m pytest tests/unit/infrastructure/ tests/integration/`
- `uv run python -m mypy --strict src/bioetl/infrastructure/`

## Risks & Requires Manual Review
- None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-adapters-chembl | tests/unit/infrastructure/adapters/chembl/ | DONE | Passed |
| 2 | L3-adapters-pubmed | tests/unit/infrastructure/adapters/pubmed/ | DONE | Passed |
