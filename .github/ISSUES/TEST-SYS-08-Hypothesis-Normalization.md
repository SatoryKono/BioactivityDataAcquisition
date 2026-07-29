---
title: "[P2][testing] TEST-SYS-08: Hypothesis for identifier/normalization families"
labels: P2, testing, domain, determinism, quality, coverage
assignees: []
github_issue: 7030
---

## Context

Hypothesis usage is sparse (~**29** marker hits). Aggregates already have property
tests; identifier/normalization families are under-fuzzed relative to hash risk.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §4 C5, P2-2  
**Epic:** TEST-SYS-00

## Problem

Table tests miss combinatorial edge cases on IDs, case folding, empty/null,
ordering, and unicode that break deterministic identity.

## Scope / modules

- `tests/unit/domain/normalization/**`
- identifier canonicalization helpers
- Existing aggregate property tests as style reference (`tests/unit/domain/aggregates/**`)

## Acceptance Criteria

- [ ] Add Hypothesis strategies for top identifier families (provider-scoped where needed)
- [ ] Properties: idempotence of normalize, determinism of order/hash inputs, reject invalid shapes
- [ ] Tests remain pure unit (no network/FS); fixed seeds where required for CI stability
- [ ] Document strategy placement (no one-off random in production code paths)

## Related

- TEST-SYS-07 (coverage floors)
- `tests/architecture/test_no_random_in_writers.py`
