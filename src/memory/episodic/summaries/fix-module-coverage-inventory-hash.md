---
id: fix-module-coverage-inventory-hash
title: Fix module coverage inventory source-tree hash drift
task_id: fix-module-coverage-inventory-hash
created_at: '2026-05-25T16:38:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_module_coverage_inventory.py
summary: Regenerated the committed module-coverage inventory from the current coverage
  XML so the recorded source-tree SHA matches the current src/bioetl snapshot and
  the architecture guard passes again.
---

# Episodic summary

## Task

- Title: Fix module coverage inventory source-tree hash drift

## Outcome

- Regenerated the committed module-coverage inventory from the current coverage XML so the recorded source-tree SHA matches the current src/bioetl snapshot and the architecture guard passes again.

## Lessons learned

- Replace with durable follow-up if needed
