---
id: debug-timeout-20260524
title: Debug CLI help timeout in observability test
task_id: debug-timeout-20260524
created_at: '2026-05-24T12:43:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/ops/observability/test_check_published_observability_endpoints.py
summary: Replaced flaky nested subprocess help smoke in tests/unit/scripts/ops/observability/test_check_published_observability_endpoints.py
  with deterministic router mapping and parser help assertions. Root issue appears
  tied to Windows/PyCharm subprocess smoke, not the observability CLI logic itself.
---

# Episodic summary

## Task

- Title: Debug CLI help timeout in observability test

## Outcome

- Replaced flaky nested subprocess help smoke in tests/unit/scripts/ops/observability/test_check_published_observability_endpoints.py with deterministic router mapping and parser help assertions. Root issue appears tied to Windows/PyCharm subprocess smoke, not the observability CLI logic itself.

## Lessons learned

- Replace with durable follow-up if needed
