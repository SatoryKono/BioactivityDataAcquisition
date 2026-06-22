---
id: private-module-import-fix-20260622
title: Fix private module import violation
task_id: private-module-import-fix-20260622
created_at: '2026-06-22T08:17:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/run_manifest_output_support.py
summary: Added a public CLI run-manifest output support facade and rewired the maintenance
  planner to stop importing the private owner-local helper module directly.
---

# Episodic summary

## Task

- Title: Fix private module import violation

## Outcome

- Added a public CLI run-manifest output support facade and rewired the maintenance planner to stop importing the private owner-local helper module directly.

## Lessons learned

- Replace with durable follow-up if needed
