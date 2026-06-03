---
id: fix-runtime-metric-replay-emitter-20260603
title: Fix runtime replay metric emitter ownership
task_id: fix-runtime-metric-replay-emitter-20260603
created_at: '2026-06-03T06:46:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Moved replay reconstructability metric emission calls into _run_manifest_creation_support.py
  and kept a compatibility shim in policy module. Verified integration metric ownership
  test and replay metric unit tests.
---

# Episodic summary

## Task

- Title: Fix runtime replay metric emitter ownership

## Outcome

- Moved replay reconstructability metric emission calls into _run_manifest_creation_support.py and kept a compatibility shim in policy module. Verified integration metric ownership test and replay metric unit tests.

## Lessons learned

- Replace with durable follow-up if needed
