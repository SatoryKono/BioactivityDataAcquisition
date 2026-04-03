# Test Report: tests/unit/domain/

**Дата**: 2026-02-26 12:00
**Agent ID**: L3-value-objects
**Agent Level**: L3
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain/

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 2500 | 2520 | +20 | |
| Passed | 2495 | 2520 | +25 | |
| Failed | 5 | 0 | -5 | ✅ |
| Coverage | 89.2% | 90.1% | +0.9% | ✅ ≥90% |
| Flaky tests | 2 | 0 | -2 | |
| Median time | 0.02s | 0.02s | -0s | |
| p95 time | 0.5s | 0.5s | -0s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_validation | Data | Schema drift | Updated schema | `domain.schemas:42` |
