---
id: interfaces-composition-seam-fix
title: Fix interfaces composition import seams
task_id: interfaces-composition-seam-fix
created_at: '2026-05-31T18:04:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_forbidden_imports.py
summary: Moved health and maintenance CLI composition imports onto sanctioned health_api/maintenance_api
  seams, removed direct interfaces imports of services_api/resources_api/bootstrap/config_access,
  and revalidated targeted forbidden-import tests plus refreshed module coverage hash.
---

# Episodic summary

## Task

- Title: Fix interfaces composition import seams

## Outcome

- Moved health and maintenance CLI composition imports onto sanctioned health_api/maintenance_api seams, removed direct interfaces imports of services_api/resources_api/bootstrap/config_access, and revalidated targeted forbidden-import tests plus refreshed module coverage hash.

## Lessons learned

- Replace with durable follow-up if needed
