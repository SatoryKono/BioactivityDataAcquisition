---
id: debug-cli-run-all-timeout-20260603
title: Debug run-all CLI timeout
task_id: debug-cli-run-all-timeout-20260603
created_at: '2026-06-03T05:47:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_cli_run_all_vacuum_formatters.py
summary: Isolated run-all CLI unit tests from real observability backend startup by
  mocking backend ensure/disable seams in the run_all-vacuum-formatters test module;
  the previously timing-out failure case and the full test module now pass.
---

# Episodic summary

## Task

- Title: Debug run-all CLI timeout

## Outcome

- Isolated run-all CLI unit tests from real observability backend startup by mocking backend ensure/disable seams in the run_all-vacuum-formatters test module; the previously timing-out failure case and the full test module now pass.

## Lessons learned

- Replace with durable follow-up if needed
