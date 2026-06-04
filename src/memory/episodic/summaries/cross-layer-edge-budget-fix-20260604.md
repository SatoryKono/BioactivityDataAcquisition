---
id: cross-layer-edge-budget-fix-20260604
title: Fix cross-layer edge budget regression
task_id: cross-layer-edge-budget-fix-20260604
created_at: '2026-06-04T15:00:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/control_plane_store_builders.py
summary: Reduced cross-layer group edges back under budget by removing the type-only
  domain.ports import from composition.control_plane_store_builders while preserving
  runtime behavior. Confirmed the regression metric passes, kept the Silver metadata
  compatibility shim green, and refreshed module coverage inventory plus the source-tree
  hash guard after the src edits.
---

# Episodic summary

## Task

- Title: Fix cross-layer edge budget regression

## Outcome

- Reduced cross-layer group edges back under budget by removing the type-only domain.ports import from composition.control_plane_store_builders while preserving runtime behavior. Confirmed the regression metric passes, kept the Silver metadata compatibility shim green, and refreshed module coverage inventory plus the source-tree hash guard after the src edits.

## Lessons learned

- Replace with durable follow-up if needed
