---
id: dbg-cli-helper-timeout
title: Debug CLI helper timeout in observability backend probes
task_id: dbg-cli-helper-timeout
created_at: '2026-06-02T08:30:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_cli_helpers.py
summary: Patched test_cli_helpers.py with an autouse observability-backend ensure
  mock so run-command unit tests no longer start or probe the detached backend through
  real HTTP.
---

# Episodic summary

## Task

- Title: Debug CLI helper timeout in observability backend probes

## Outcome

- Patched test_cli_helpers.py with an autouse observability-backend ensure mock so run-command unit tests no longer start or probe the detached backend through real HTTP.

## Lessons learned

- Replace with durable follow-up if needed
