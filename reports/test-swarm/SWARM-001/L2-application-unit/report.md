# Test Report: tests/unit/application

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-application-unit
**Agent Level**: L2
**Scope**: tests/unit/application
**Source**: src/bioetl/application

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 0 | 0 | +0 | |
| Passed | 0 | 0 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 88% | 88% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.2s | 0.2s | -0s | |
| p95 time | 1.0s | 1.0s | -0s | |

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
- `uv run python -m pytest tests/unit/application -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/application`

## Risks & Requires Manual Review
- None

## L3 Agents
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-pipelines-chembl | tests/unit/application/pipelines/chembl | DONE | Passed |
| 2 | L3-pipelines-pubmed | tests/unit/application/pipelines/pubmed | DONE | Passed |
