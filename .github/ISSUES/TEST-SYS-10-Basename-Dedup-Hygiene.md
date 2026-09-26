---
title: "[P2][testing] TEST-SYS-10: Basename dedup / multi-provider test naming hygiene"
labels: P2, testing, hygiene, refactor, quality
assignees: []
github_issue: 7032
---

## Context

Audit found **~70** duplicate `test_*.py` basenames across trees (e.g.
`test_request_metadata.py` ×7). Not always wrong (provider-scoped), but hurts
navigation, tooling, and accidental collect confusion.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §3 S3, P2-1  
**Epic:** TEST-SYS-00

## Problem

Same basename across providers obscures ownership; merge/refactor risk increases.

## Scope / modules

- Multi-provider trees under `tests/unit/**`, `tests/integration/**`
- Optional rename + re-export shims only if required for imports (prefer path-unique names)

## Acceptance Criteria

- [ ] Inventory duplicate basenames with path list (generated report under `reports/quality/` or docs evidence)
- [ ] Rename or consolidate high-churn collisions (start with request_metadata / adapter metadata families)
- [ ] Prefer parametrized shared module **or** provider-prefixed filenames (`test_chembl_request_metadata.py`)
- [ ] Update any hard-coded path references in architecture inventories
- [ ] No behavior change; green targeted tests

## Related

- TEST-SYS-03 (closeout consolidation — separate)
