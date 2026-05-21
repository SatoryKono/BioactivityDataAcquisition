---
id: private-import-guard-20260521
title: Fix private module import guard
task_id: private-import-guard-20260521
created_at: '2026-05-21T09:40:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Replaced TYPE_CHECKING-only import of Settings from private bioetl.infrastructure.config._base
  with the public bioetl.infrastructure.config seam in _run_manifest_refs.py. Validated
  the private-module architecture guard and py_compile.
---

# Episodic summary

## Task

- Title: Fix private module import guard

## Outcome

- Replaced TYPE_CHECKING-only import of Settings from private bioetl.infrastructure.config._base with the public bioetl.infrastructure.config seam in _run_manifest_refs.py. Validated the private-module architecture guard and py_compile.

## Lessons learned

- Replace with durable follow-up if needed
