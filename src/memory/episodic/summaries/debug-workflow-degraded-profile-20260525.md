---
id: debug-workflow-degraded-profile-20260525
title: Debug workflow degraded_observable profile promotion
task_id: debug-workflow-degraded-profile-20260525
created_at: '2026-05-25T03:50:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/run_manifest_service.py
- tests/unit/application/services/test_run_manifest_service.py
summary: Confirmed chembl_activity degraded_observable is promoted to replay_ready
  by replay-capable family policy; improved dirty-source strict manifest error to
  include configured profile, effective profile, pipeline, and promotion marker; verified
  targeted manifest tests on WSL and Windows.
---

# Episodic summary

## Task

- Title: Debug workflow degraded_observable profile promotion

## Outcome

- Confirmed chembl_activity degraded_observable is promoted to replay_ready by replay-capable family policy; improved dirty-source strict manifest error to include configured profile, effective profile, pipeline, and promotion marker; verified targeted manifest tests on WSL and Windows.

## Lessons learned

- Replace with durable follow-up if needed
