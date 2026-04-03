# Test Report: tests/unit/application/

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-pipelines-chembl
**Agent Level**: L3
**Scope**: tests/unit/application/
**Source**: src/bioetl/application/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 2000 | 2000 | 0 | |
| Passed | 1996 | 2000 | +4 | |
| Failed | 4 | 0 | -4 | ✅ |
| Coverage | 84.1% | 85.0% | +0.9% | ✅ ≥85% |
| Flaky tests | 0 | 0 | 0 | |
| Median time | 0.05s | 0.05s | 0s | |
| p95 time | 1.0s | 1.0s | 0s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_app | Type | Protocol | Fixed protocol | `application.pipelines:42` |
