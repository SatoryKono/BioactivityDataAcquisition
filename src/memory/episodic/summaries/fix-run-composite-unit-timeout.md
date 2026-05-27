---
id: fix-run-composite-unit-timeout
title: Fix run_composite unit timeout from metrics gateway bootstrap
task_id: fix-run-composite-unit-timeout
created_at: '2026-05-26T05:49:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/commands/test_run_composite.py
summary: Added an autouse run-composite CLI unit-test fixture that patches composite
  support push_metrics_to_gateway, preventing mocked CLI runs from bootstrapping real
  observability/metrics composition during finally cleanup. Validated ruff, Windows
  single/full module pytest, and Linux single pytest.
---

# Episodic summary

## Task

- Title: Fix run_composite unit timeout from metrics gateway bootstrap

## Outcome

- Added an autouse run-composite CLI unit-test fixture that patches composite support push_metrics_to_gateway, preventing mocked CLI runs from bootstrapping real observability/metrics composition during finally cleanup. Validated ruff, Windows single/full module pytest, and Linux single pytest.

## Lessons learned

- Replace with durable follow-up if needed
