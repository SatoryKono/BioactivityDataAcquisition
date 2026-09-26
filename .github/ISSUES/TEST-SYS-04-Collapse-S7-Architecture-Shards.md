---
title: "[P1][testing] TEST-SYS-04: Collapse redundant S7 architecture shards"
labels: P1, testing, architecture-tests, ci, performance, config
assignees: []
github_issue: 7026
---

## Context

`configs/quality/pytest_shards.yaml` defines **15** shards; **7** are architecture
variants rooted at `tests/architecture` with different ignore globs — repeated
collection cost.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §2.5, P1-2  
**Epic:** TEST-SYS-00

## Problem

S7-a / a2 / a3 / b / c / d / guardrails re-walk the same tree. Intentional isolation
is fine; redundant fan-out is not free.

## Scope / modules

- `configs/quality/pytest_shards.yaml`
- `configs/quality/test_matrix.yaml`
- CI workflow shard matrix consumers
- Architecture tests that assume shard-specific ignores

## Acceptance Criteria

- [ ] Document current S7 shard purpose matrix (ignore sets, worker overrides)
- [ ] Reduce architecture shard count by **≥2** where ignore sets allow merge **or** replace multi-collect with single collect + filter/nodeid selection
- [ ] Keep serial isolation where VCR/shared FS risk exists (`workers_override: 0` where required)
- [ ] CI architecture lane green; no accidental drop of guardrail coverage
- [ ] Shard inventory governance tests updated

## Related

- TEST-SYS-03 (closeout content reduction amplifies shard gains)
- Keep `forbid_global_xdist_addopts: true`
