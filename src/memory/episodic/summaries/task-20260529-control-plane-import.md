---
id: task-20260529-control-plane-import
title: Fix control plane replay import regression for historical replay certification
  tests
task_id: task-20260529-control-plane-import
created_at: '2026-05-29T18:17:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added compatibility resolver import path in _run_manifest_diagnostics_replay_projection
  to avoid ImportError when replay-readiness symbol is unavailable in primary module
  shape.
---

# Episodic summary

## Task

- Title: Fix control plane replay import regression for historical replay certification tests

## Outcome

- Added compatibility resolver import path in _run_manifest_diagnostics_replay_projection to avoid ImportError when replay-readiness symbol is unavailable in primary module shape.

## Lessons learned

- Replace with durable follow-up if needed
