---
id: control-plane-replay-import-regression
title: Restore replay diagnostics compatibility exports
task_id: control-plane-replay-import-regression
created_at: '2026-05-16T13:21:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/_run_manifest_diagnostics_replay.py
summary: Re-exported replay-boundary helpers from _run_manifest_diagnostics_replay
  so control-plane service imports no longer fail after module split.
---

# Episodic summary

## Task

- Title: Restore replay diagnostics compatibility exports

## Outcome

- Re-exported replay-boundary helpers from _run_manifest_diagnostics_replay so control-plane service imports no longer fail after module split.

## Lessons learned

- Replace with durable follow-up if needed
