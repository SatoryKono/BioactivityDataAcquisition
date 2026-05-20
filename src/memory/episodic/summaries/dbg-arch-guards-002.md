---
id: dbg-arch-guards-002
title: Fix compatibility freeze guards, domain purity, ruff, and test structural debt
  regressions
task_id: DBG-ARCH-GUARDS-002
created_at: '2026-05-20T06:45:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added missing bootstrap package _PUBLIC_EXPORTS freeze-guard literal, switched
  PipelineConfig to the public bioetl.domain.composite.config entrypoint, moved CSV-backed
  organism coverage out of tests/unit/domain into integration scope, and cleaned remaining
  ruff issues in touched modules. Verified the originally failing architecture/regression
  tests, ruff budget, and direct unit/integration surfaces.
---

# Episodic summary

## Task

- Title: Fix compatibility freeze guards, domain purity, ruff, and test structural debt regressions

## Outcome

- Added missing bootstrap package _PUBLIC_EXPORTS freeze-guard literal, switched PipelineConfig to the public bioetl.domain.composite.config entrypoint, moved CSV-backed organism coverage out of tests/unit/domain into integration scope, and cleaned remaining ruff issues in touched modules. Verified the originally failing architecture/regression tests, ruff budget, and direct unit/integration surfaces.

## Lessons learned

- Replace with durable follow-up if needed
