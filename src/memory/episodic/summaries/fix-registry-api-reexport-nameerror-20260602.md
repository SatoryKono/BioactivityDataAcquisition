---
id: fix-registry-api-reexport-nameerror-20260602
title: Fix registry_api canonical reexport NameError
task_id: fix-registry-api-reexport-nameerror-20260602
created_at: '2026-06-02T16:27:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed test_canonical_module_paths.py to import canonical get_default_registry
  from bioetl.composition.registry before comparing the registry_api re-export. Verified
  ruff and the target composition test module pass.
---

# Episodic summary

## Task

- Title: Fix registry_api canonical reexport NameError

## Outcome

- Fixed test_canonical_module_paths.py to import canonical get_default_registry from bioetl.composition.registry before comparing the registry_api re-export. Verified ruff and the target composition test module pass.

## Lessons learned

- Replace with durable follow-up if needed
