---
id: fix-hotspot-family-budget-20260516
title: Fix hotspot family file-growth budget drift
task_id: fix-hotspot-family-budget-20260516
created_at: '2026-05-16T10:24:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Restored application_core hotspot-family growth compliance by reducing batch_checkpoint_recovery_service.py
  from 250 to 249 lines without behavior changes, bringing the >=250 LOC file count
  back to the reviewed budget of 14.
---

# Episodic summary

## Task

- Title: Fix hotspot family file-growth budget drift

## Outcome

- Restored application_core hotspot-family growth compliance by reducing batch_checkpoint_recovery_service.py from 250 to 249 lines without behavior changes, bringing the >=250 LOC file count back to the reviewed budget of 14.

## Lessons learned

- Replace with durable follow-up if needed
