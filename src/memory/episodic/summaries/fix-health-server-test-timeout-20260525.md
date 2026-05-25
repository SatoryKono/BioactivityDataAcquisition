---
id: fix-health-server-test-timeout-20260525
title: Fix health server unit test timeout
task_id: fix-health-server-test-timeout-20260525
created_at: '2026-05-25T16:13:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
- tests/unit/interfaces/cli/commands/test_health.py
summary: Removed health server CLI unit-test timeout by avoiding eager root registry
  bootstrap and by patching health observability in async lifecycle tests; targeted
  CLI tests pass.
---

# Episodic summary

## Task

- Title: Fix health server unit test timeout

## Outcome

- Removed health server CLI unit-test timeout by avoiding eager root registry bootstrap and by patching health observability in async lifecycle tests; targeted CLI tests pass.

## Lessons learned

- Health CLI lifecycle tests must mock long-lived observability seams separately
  from `HealthServer` start/stop so unit tests do not bootstrap metrics services.
