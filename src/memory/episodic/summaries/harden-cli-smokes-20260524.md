---
id: harden-cli-smokes-20260524
title: Harden router CLI smoke tests against nested subprocess hangs
task_id: harden-cli-smokes-20260524
created_at: '2026-05-24T12:49:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/helpers/cli_process.py tests/helpers/__init__.py tests/unit/scripts/ops/observability/test_check_published_observability_endpoints.py
summary: Added in-process CLI test helper run_main_in_process plus assert_router_python_command,
  exported them from tests.helpers, and converted the observability router smoke to
  avoid nested subprocess help execution that was timing out on Windows/PyCharm.
---

# Episodic summary

## Task

- Title: Harden router CLI smoke tests against nested subprocess hangs

## Outcome

- Added in-process CLI test helper run_main_in_process plus assert_router_python_command, exported them from tests.helpers, and converted the observability router smoke to avoid nested subprocess help execution that was timing out on Windows/PyCharm.

## Lessons learned

- Replace with durable follow-up if needed
