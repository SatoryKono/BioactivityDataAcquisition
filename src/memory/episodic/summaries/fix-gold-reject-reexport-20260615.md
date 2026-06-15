---
id: fix-gold-reject-reexport-20260615
title: Fix GoldRejectReason import regression
task_id: fix-gold-reject-reexport-20260615
created_at: '2026-06-15T11:34:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/services/__init__.py
summary: Extended the fix to restore lazy services package submodule exports for factory
  and bundle so patch-based pipeline factory tests and Gold reject taxonomy imports
  both resolve through the public facades again.
---

# Episodic summary

## Task

- Title: Fix GoldRejectReason import regression

## Outcome

- Extended the fix to restore lazy services package submodule exports for factory and bundle so patch-based pipeline factory tests and Gold reject taxonomy imports both resolve through the public facades again.

## Lessons learned

- Replace with durable follow-up if needed
