---
title: "[P1][testing] TEST-SYS-05: Expand unit-parallel-safe + enforce repo_backed exclusion"
labels: P1, testing, ci, performance, quality, governance
assignees: []
github_issue: 7027
---

## Context

Local/default pytest is **serial**; global xdist is forbidden. Speed gains must
come from **opt-in** `unit-parallel-safe` membership, not relaxing determinism.
Unit lane still includes `repo_backed` hybrids that block pure parallel unit runs.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §3 S2, P1-3/P1-6  
**Epic:** TEST-SYS-00  
**Prior:** TEST-AUDIT-002

## Problem

- Pure unit tests mixed with repo-touching tests under `tests/unit`
- Parallel allowlist underused → slow local feedback without architecture justification

## Scope / modules

- `configs/quality/test_matrix.yaml` (`unit-parallel-safe`, markers policy)
- `tests/unit/repo_backed/**`
- pytest markers: `unit`, `repo_backed`, `serial`, `vcr`
- CI unit shards

## Acceptance Criteria

- [ ] Document membership rules for `unit-parallel-safe` (no FS repo writes, no VCR, no shared global state)
- [ ] Expand allowlist with measured safe modules (incremental, evidence-backed)
- [ ] CI select excludes `repo_backed` from pure unit-parallel jobs
- [ ] Architecture or matrix test enforces marker hygiene (fail on unmarked hybrid)
- [ ] No global xdist; determinism gates green

## Related

- TEST-SYS-04 (shards)
- pytest-xdist present but opt-in only
