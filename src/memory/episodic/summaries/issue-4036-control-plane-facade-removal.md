---
id: issue-4036-control-plane-facade-removal
title: Issue 4036 control-plane facade removal wave
task_id: issue-4036-control-plane-facade-removal
created_at: '2026-05-13T16:19:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed run_manifest_inspection_service.py and run_ledger_service.py facades,
  moved callers to canonical control_plane owners, synced active governance references,
  and passed targeted pytest via the repo wrapper; memory refresh still requires skip-refresh
  because generated retrieval surfaces can lag removal waves.
---

# Episodic summary

## Task

- Title: Issue 4036 control-plane facade removal wave

## Outcome

- Removed run_manifest_inspection_service.py and run_ledger_service.py facades, moved callers to canonical control_plane owners, synced active governance references, and passed targeted pytest via the repo wrapper; memory refresh still requires skip-refresh because generated retrieval surfaces can lag removal waves.

## Lessons learned

- Replace with durable follow-up if needed
