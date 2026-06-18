---
id: ruff-up035-fix
title: Fix UP035 import in protein_class_target_type_helpers
task_id: ruff-up035-fix
created_at: '2026-06-18T07:55:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/mapping/protein_class_target_type_helpers.py
summary: Moved Callable import to collections.abc in protein_class_target_type_helpers
  to satisfy Ruff UP035 and verified the targeted regression metric and file-level
  ruff check.
---

# Episodic summary

## Task

- Title: Fix UP035 import in protein_class_target_type_helpers

## Outcome

- Moved Callable import to collections.abc in protein_class_target_type_helpers to satisfy Ruff UP035 and verified the targeted regression metric and file-level ruff check.

## Lessons learned

- Replace with durable follow-up if needed
