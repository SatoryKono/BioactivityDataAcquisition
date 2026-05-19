---
id: chembl-activity-replay-ready
title: Debug chembl_activity replay_ready snapshot requirement
task_id: chembl-activity-replay-ready
created_at: '2026-05-19T03:53:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/_workflow_run_support.py
summary: Added workflow CLI fail-fast validation for strict persistence profiles and
  exact replay when snapshot-backed cached Bronze inputs are not configured; workflow
  run now exits with CONFIG_ERROR and guidance to use --use-cached-bronze or lower
  the required persistence profile. Verified with workflow CLI unit tests, neighboring
  run-orchestration tests, and a direct CLI invocation.
---

# Episodic summary

## Task

- Title: Debug chembl_activity replay_ready snapshot requirement

## Outcome

- Added workflow CLI fail-fast validation for strict persistence profiles and exact replay when snapshot-backed cached Bronze inputs are not configured; workflow run now exits with CONFIG_ERROR and guidance to use --use-cached-bronze or lower the required persistence profile. Verified with workflow CLI unit tests, neighboring run-orchestration tests, and a direct CLI invocation.

## Lessons learned

- Replace with durable follow-up if needed
