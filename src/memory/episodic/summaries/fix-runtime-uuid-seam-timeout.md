---
id: fix-runtime-uuid-seam-timeout
title: Fix runtime UUID seam inventory timeout
task_id: fix-runtime-uuid-seam-timeout
created_at: '2026-05-30T08:26:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_runtime_uuid_seam_inventory.py
summary: Optimized runtime UUID seam inventory test to prefilter candidate files with
  rg/git grep before AST parsing, avoiding full scans of application/composition trees
  on slow Windows/WSL mounts while preserving the same seam assertions.
---

# Episodic summary

## Task

- Title: Fix runtime UUID seam inventory timeout

## Outcome

- Optimized runtime UUID seam inventory test to prefilter candidate files with rg/git grep before AST parsing, avoiding full scans of application/composition trees on slow Windows/WSL mounts while preserving the same seam assertions.

## Lessons learned

- Replace with durable follow-up if needed
