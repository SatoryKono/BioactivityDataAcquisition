# Test Report: tests/unit/application/

**Дата**: 2026-02-26 12:00
**Agent ID**: L2-application-unit
**Agent Level**: L2
**Scope**: tests/unit/application/
**Source**: src/bioetl/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 830 | 830 | +0 | |
| Passed | 830 | 830 | +0 | |
| Failed | 0 | 0 | +0 | ✅ |
| Coverage | 86% | 86% | +0% | ✅ ≥85% |
| Flaky tests | 0 | 0 | -0 | |
| Median time | 0.05s | 0.05s | -0.0s | |
| p95 time | 0.2s | 0.2s | -0.0s | |

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
- `uv run python -m pytest tests/... -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/...`

## Risks & Requires Manual Review
- Dependency on external service in test_Y
