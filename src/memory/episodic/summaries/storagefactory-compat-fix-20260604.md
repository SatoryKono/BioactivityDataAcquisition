---
id: storagefactory-compat-fix-20260604
title: Fix StorageFactory compatibility seam in common_service_wiring
task_id: storagefactory-compat-fix-20260604
created_at: '2026-06-04T12:31:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/services/common_service_wiring.py
- tests/unit/composition/factories/services/test_common_service_wiring.py
- tests/integration/pipelines/base.py
summary: Restored a module-level lazy StorageFactory seam in common_service_wiring
  so existing patch targets keep working, added a regression test for the fallback
  path, verified integration setup no longer fails with AttributeError, and confirmed
  the committed module coverage source_tree_sha256 already matches the current src
  tree.
---

# Episodic summary

## Task

- Title: Fix StorageFactory compatibility seam in common_service_wiring

## Outcome

- Restored a module-level lazy StorageFactory seam in common_service_wiring so existing patch targets keep working, added a regression test for the fallback path, verified integration setup no longer fails with AttributeError, and confirmed the committed module coverage source_tree_sha256 already matches the current src tree.

## Lessons learned

- Replace with durable follow-up if needed
