---
id: ports-facade-import-fix
title: Fix direct ports submodule imports
task_id: ports-facade-import-fix
created_at: '2026-06-01T06:08:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_forbidden_imports.py
summary: Replaced direct imports from bioetl.domain.ports.health_check and bioetl.domain.ports.protein_classification
  with sanctioned facade imports from bioetl.domain.ports in application/composition/infrastructure
  callers, then revalidated forbidden-import architecture guard and refreshed module
  coverage source-tree hash.
---

# Episodic summary

## Task

- Title: Fix direct ports submodule imports

## Outcome

- Replaced direct imports from bioetl.domain.ports.health_check and bioetl.domain.ports.protein_classification with sanctioned facade imports from bioetl.domain.ports in application/composition/infrastructure callers, then revalidated forbidden-import architecture guard and refreshed module coverage source-tree hash.

## Lessons learned

- Replace with durable follow-up if needed
