---
id: 20260529-fix-run-manifest-replay-import
title: Fix ImportError for _resolve_manifest_replay_readiness_verdict in run_manifest_diagnostics_replay
task_id: 20260529-fix-run-manifest-replay-import
created_at: '2026-05-29T18:14:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Moved replay readiness verdict import in projection module to private owner
  module to avoid missing public re-export and resolved test import-time failure in
  run manifest commands.
---

# Episodic summary

## Task

- Title: Fix ImportError for _resolve_manifest_replay_readiness_verdict in run_manifest_diagnostics_replay

## Outcome

- Moved replay readiness verdict import in projection module to private owner module to avoid missing public re-export and resolved test import-time failure in run manifest commands.

## Lessons learned

- Replace with durable follow-up if needed
