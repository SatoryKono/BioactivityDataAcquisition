---
id: storage-factory-compat-fix
title: Restore StorageFactory patch seam in services factory
task_id: storage-factory-compat-fix
created_at: '2026-06-04T09:59:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/services/factory.py
summary: Restored module-level StorageFactory and service port factory patch seams
  in bioetl.composition.factories.services.factory after tests failed with AttributeError
  for services.factory.StorageFactory. create_common_services now uses the module-level
  StorageFactory symbol so existing tests and integration patch paths intercept StorageFactory.create.
  Reran ruff, services factory/smoke/canonical tests, direct import smoke, refreshed
  module coverage inventory, and passed source_tree hash guard.
---

# Episodic summary

## Task

- Title: Restore StorageFactory patch seam in services factory

## Outcome

- Restored module-level StorageFactory and service port factory patch seams in bioetl.composition.factories.services.factory after tests failed with AttributeError for services.factory.StorageFactory. create_common_services now uses the module-level StorageFactory symbol so existing tests and integration patch paths intercept StorageFactory.create. Reran ruff, services factory/smoke/canonical tests, direct import smoke, refreshed module coverage inventory, and passed source_tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
