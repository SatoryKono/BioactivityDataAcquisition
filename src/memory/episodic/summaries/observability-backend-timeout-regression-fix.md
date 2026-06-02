---
id: observability-backend-timeout-regression-fix
title: Fix CLI integration timeout regression from observability backend auto-start
task_id: observability-backend-timeout-regression-fix
created_at: '2026-06-01T19:22:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Patched the CLI integration test fixture layer to replace detached observability
  backend startup with a disabled no-op result across run/run-all/run-composite/workflow
  commands, keeping integration CLI tests free from network and subprocess side effects
  after the observability backend refactor.
---

# Episodic summary

## Task

- Title: Fix CLI integration timeout regression from observability backend auto-start

## Outcome

- Patched the CLI integration test fixture layer to replace detached observability backend startup with a disabled no-op result across run/run-all/run-composite/workflow commands, keeping integration CLI tests free from network and subprocess side effects after the observability backend refactor.

## Lessons learned

- Replace with durable follow-up if needed
