---
id: fix-run-manifest-diagnostics-replay-loc-20260516
title: Fix application LOC violation for run manifest diagnostics replay module
task_id: fix-run-manifest-diagnostics-replay-loc-20260516
created_at: '2026-05-16T08:48:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/_run_manifest_diagnostics_replay.py
- src/bioetl/application/services/control_plane/_run_manifest_diagnostics_replay_helpers.py
summary: Moved replay profile and parentage helpers into the existing replay helper
  module to bring the application replay diagnostics module back under the 500 LOC
  architecture limit without changing behavior.
---

# Episodic summary

## Task

- Title: Fix application LOC violation for run manifest diagnostics replay module

## Outcome

- Moved replay profile and parentage helpers into the existing replay helper module to bring the application replay diagnostics module back under the 500 LOC architecture limit without changing behavior.

## Lessons learned

- Replace with durable follow-up if needed
