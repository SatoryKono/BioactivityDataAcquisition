---
id: fix-resource-management-freeze-guard-unit-imports-20260622
title: Fix resource management freeze guard unit imports
task_id: fix-resource-management-freeze-guard-unit-imports-20260622
created_at: '2026-06-22T16:28:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_compatibility_freeze_guards_provider_datasource.py
summary: Investigated architecture freeze guard failure for direct unit imports of
  bioetl.composition._resource_management from tests/unit/composition/test_canonical_module_paths.py.
  Current checkout already routes those assertions through public bioetl.composition.resources_api
  instead of the internal module, while dedicated test_resource_management.py remains
  the allowed internal seam test. Validation passed for the freeze guard parametrization
  and canonical module paths unit tests; no additional source edits were required
  in this turn.
---

# Episodic summary

## Task

- Title: Fix resource management freeze guard unit imports

## Outcome

- Investigated architecture freeze guard failure for direct unit imports of bioetl.composition._resource_management from tests/unit/composition/test_canonical_module_paths.py. Current checkout already routes those assertions through public bioetl.composition.resources_api instead of the internal module, while dedicated test_resource_management.py remains the allowed internal seam test. Validation passed for the freeze guard parametrization and canonical module paths unit tests; no additional source edits were required in this turn.

## Lessons learned

- Replace with durable follow-up if needed
