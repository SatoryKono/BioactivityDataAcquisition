---
id: ruff-budget-fix-20260616
title: Fix ruff regression budget failure
task_id: ruff-budget-fix-20260616
created_at: '2026-06-16T08:47:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/debug_export_helpers.py
summary: Removed the unused pathlib.Path import from debug_export_helpers.py, re-ran
  targeted ruff and the regression-metrics budget test, and refreshed reports/quality/module-coverage-inventory.json
  source_tree_sha256.
---

# Episodic summary

## Task

- Title: Fix ruff regression budget failure

## Outcome

- Removed the unused pathlib.Path import from debug_export_helpers.py, re-ran targeted ruff and the regression-metrics budget test, and refreshed reports/quality/module-coverage-inventory.json source_tree_sha256.

## Lessons learned

- Replace with durable follow-up if needed
