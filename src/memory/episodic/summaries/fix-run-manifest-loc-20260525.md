---
id: fix-run-manifest-loc-20260525
title: Fix run_manifest LOC architecture failure
task_id: fix-run-manifest-loc-20260525
created_at: '2026-05-25T12:43:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/run_manifest.py
summary: Reduced src/bioetl/domain/control_plane/run_manifest.py from 309 to 303 LOC
  by compressing __post_init__ immutable-setattr calls without changing manifest semantics.
  Targeted architecture and manifest tests pass.
---

# Episodic summary

## Task

- Title: Fix run_manifest LOC architecture failure

## Outcome

- Reduced src/bioetl/domain/control_plane/run_manifest.py from 309 to 303 LOC by compressing __post_init__ immutable-setattr calls without changing manifest semantics. Targeted architecture and manifest tests pass.

## Lessons learned

- For file-size architecture failures, prefer removing local formatting overhead
  before adding or increasing `file_size_limits` exemptions.
