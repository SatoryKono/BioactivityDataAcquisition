---
id: fix-arch-failures-2026-05-14
title: Fix architecture drift, compat sunset, and ruff regressions
task_id: fix-arch-failures-2026-05-14
created_at: '2026-05-14T10:42:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_architecture_dependency_docs_drift.py
summary: Removed the reintroduced cli inspection_output compat wrapper, restored missing
  workflow type-only imports in composition services, cleaned ruff/style regressions
  in DQ and run-ledger helpers, and regenerated architecture dependency map artifacts
  to match the current source tree. Verified targeted ruff and the three failing architecture
  tests pass.
---

# Episodic summary

## Task

- Title: Fix architecture drift, compat sunset, and ruff regressions

## Outcome

- Removed the reintroduced cli inspection_output compat wrapper, restored missing workflow type-only imports in composition services, cleaned ruff/style regressions in DQ and run-ledger helpers, and regenerated architecture dependency map artifacts to match the current source tree. Verified targeted ruff and the three failing architecture tests pass.

## Lessons learned

- Replace with durable follow-up if needed
