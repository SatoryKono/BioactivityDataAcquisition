---
id: registry-test-seam-fix-20260602
title: Confine registry compatibility import seam in tests
task_id: registry-test-seam-fix-20260602
created_at: '2026-06-02T16:42:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/test_canonical_module_paths.py
summary: Updated tests/unit/composition/test_canonical_module_paths.py to stop importing
  bioetl.composition.registry directly. The test now validates get_default_registry
  through the sanctioned bioetl.composition.registry_api seam, satisfying the compatibility
  freeze guard without broadening direct registry imports.
---

# Episodic summary

## Task

- Title: Confine registry compatibility import seam in tests

## Outcome

- Updated tests/unit/composition/test_canonical_module_paths.py to stop importing bioetl.composition.registry directly. The test now validates get_default_registry through the sanctioned bioetl.composition.registry_api seam, satisfying the compatibility freeze guard without broadening direct registry imports.

## Lessons learned

- Replace with durable follow-up if needed
