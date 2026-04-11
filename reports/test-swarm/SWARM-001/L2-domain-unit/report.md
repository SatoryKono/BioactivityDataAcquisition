# Test Report: L2-domain-unit

**Дата**: 2026-04-11 12:00
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: L2-domain-unit scope
**Source**: src/bioetl/domain

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 5242 | 5242 | 0 | |
| Passed | 5242 | 5242 | +0 | |
| Failed | 0 | 0 | -0 | ✅ |
| Coverage | 93% | 93% | 0% | ✅ ≥85% |
| Flaky tests | 1 | 0 | -1 | |
| Median time | 0.01s | 0.01s | 0s | |
| p95 time | 0.05s | 0.05s | 0s | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | test_audit_inspection | Import | IndentationError | Fixed indent | `tests/unit/application/services/test_audit_inspection_service.py:39` |

## L3 Agents (если оркестратор)
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | scope | DONE | +0 tests, 0 fixes |
| 2 | L3-services | scope | DONE | +0 tests, 0 fixes |
| 3 | L3-value-objects | scope | DONE | +0 tests, 0 fixes |
