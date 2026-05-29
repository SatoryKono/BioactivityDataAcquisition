---
id: import-graph-inventory-census-fix-2026-05-29
title: Fix compatibility importer census test drift
task_id: import-graph-inventory-census-fix-2026-05-29
created_at: '2026-05-29T16:32:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated tests/unit/scripts/qa/test_import_graph_inventory_reports.py to derive
  removed_compatibility_surface_count from the live REMOVED_COMPATIBILITY_SURFACES
  registry instead of the stale hard-coded count 3; validated the target unit suite.
---

# Episodic summary

## Task

- Title: Fix compatibility importer census test drift

## Outcome

- Updated tests/unit/scripts/qa/test_import_graph_inventory_reports.py to derive removed_compatibility_surface_count from the live REMOVED_COMPATIBILITY_SURFACES registry instead of the stale hard-coded count 3; validated the target unit suite.

## Lessons learned

- Replace with durable follow-up if needed
