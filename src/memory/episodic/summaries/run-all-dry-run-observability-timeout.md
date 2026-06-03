---
id: run-all-dry-run-observability-timeout
title: Debug run-all dry-run observability timeout
task_id: run-all-dry-run-observability-timeout
created_at: '2026-06-03T11:03:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_run_all_command.py
summary: Fixed run-all dry-run observability backend timeout by skipping backend startup
  for dry-run and mocking backend in command-level unit tests; refreshed architecture
  dependency map and module coverage inventory.
---

# Episodic summary

## Task

- Title: Debug run-all dry-run observability timeout

## Outcome

- Fixed run-all dry-run observability backend timeout by skipping backend startup for dry-run and mocking backend in command-level unit tests; refreshed architecture dependency map and module coverage inventory.

## Lessons learned

- Replace with durable follow-up if needed
