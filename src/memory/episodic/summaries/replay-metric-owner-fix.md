---
id: replay-metric-owner-fix
title: replay metric owner fix
task_id: replay-metric-owner-fix
created_at: '2026-06-18T11:07:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Restored the ownership seam for emit_replay_reconstructability_metric by
  defining a local wrapper in _run_manifest_creation_support that delegates to the
  replay-support implementation. Verified that __module__ now points to _run_manifest_creation_support,
  the targeted runtime-builder test file passes, and ruff is clean.
---

# Episodic summary

## Task

- Title: replay metric owner fix

## Outcome

- Restored the ownership seam for emit_replay_reconstructability_metric by defining a local wrapper in _run_manifest_creation_support that delegates to the replay-support implementation. Verified that __module__ now points to _run_manifest_creation_support, the targeted runtime-builder test file passes, and ruff is clean.

## Lessons learned

- Replace with durable follow-up if needed
