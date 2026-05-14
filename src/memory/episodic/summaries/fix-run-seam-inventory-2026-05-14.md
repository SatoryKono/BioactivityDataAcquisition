---
id: fix-run-seam-inventory-2026-05-14
title: Fix run.py seam inventory regression
task_id: fix-run-seam-inventory-2026-05-14
created_at: '2026-05-14T10:53:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_cli_commands.py
summary: Updated the run CLI seam-inventory unit test to include create_cli_run_orchestration_service,
  which is a real canonical seam used to build a fresh per-command orchestration service
  distinct from the compatibility accessor. Verified the seam inventory test and the
  adjacent fresh-vs-compat wiring test pass.
---

# Episodic summary

## Task

- Title: Fix run.py seam inventory regression

## Outcome

- Updated the run CLI seam-inventory unit test to include create_cli_run_orchestration_service, which is a real canonical seam used to build a fresh per-command orchestration service distinct from the compatibility accessor. Verified the seam inventory test and the adjacent fresh-vs-compat wiring test pass.

## Lessons learned

- Replace with durable follow-up if needed
