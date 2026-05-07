---
id: run-execution-request-rename
title: Rename RunExecutionSpec to RunExecutionRequest
task_id: run-execution-request-rename
created_at: '2026-05-07T10:47:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/execution/cli_run_orchestration_models.py
summary: Promoted RunExecutionRequest to the sole canonical CLI execution model name,
  removed RunExecutionSpec export/alias, added regression coverage, and validated
  targeted pytest plus narrow mypy.
---

# Episodic summary

## Task

- Title: Rename RunExecutionSpec to RunExecutionRequest

## Outcome

- Promoted RunExecutionRequest to the sole canonical CLI execution model name, removed RunExecutionSpec export/alias, added regression coverage, and validated targeted pytest plus narrow mypy.

## Lessons learned

- Replace with durable follow-up if needed
