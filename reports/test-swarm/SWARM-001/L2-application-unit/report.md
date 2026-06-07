# Test Report: tests/unit/application/

**Дата**: 2025-06-07 10:00
**Agent ID**: L2-application-unit
**Agent Level**: L2
**Scope**: tests/unit/application/
**Source**: src/bioetl/application/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 5339 | 5339 | 0 | |
| Passed | 5339 | 5339 | 0 | |
| Failed | 0 | 0 | 0 | ✅ |
| Coverage | 86% | 86% | 0 | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.01s | 0.01s | 0 | |
| p95 time | 0.1s | 0.1s | 0 | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|

## Regression Tests Added (for fixed bugs)
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/application/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/application/`

## Risks & Requires Manual Review
- None

## L3 Agents (если оркестратор)
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-pipelines-chembl | application/pipelines/chembl | DONE | OK |
| 2 | L3-pipelines-pubmed | application/pipelines/pubmed | DONE | OK |
