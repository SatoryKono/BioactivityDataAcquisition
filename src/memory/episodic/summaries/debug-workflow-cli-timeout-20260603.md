---
id: debug-workflow-cli-timeout-20260603
title: Debug workflow CLI timeout
task_id: debug-workflow-cli-timeout-20260603
created_at: '2026-06-03T17:06:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_workflow_cli.py
summary: Prevented workflow CLI unit tests from invoking real metrics publication
  by adding an autouse test-layer stub for ensure_metrics_server_started and publish_metrics_safely;
  verified the timeout case and the full test_workflow_cli.py file.
---

# Episodic summary

## Task

- Title: Debug workflow CLI timeout

## Outcome

- Prevented workflow CLI unit tests from invoking real metrics publication by adding an autouse test-layer stub for ensure_metrics_server_started and publish_metrics_safely; verified the timeout case and the full test_workflow_cli.py file.

## Lessons learned

- Replace with durable follow-up if needed
