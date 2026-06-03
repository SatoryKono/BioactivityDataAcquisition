---
id: fix-pipeline-execution-contract-20260603
title: Fix pipeline execution contract metrics runner test
task_id: fix-pipeline-execution-contract-20260603
created_at: '2026-06-03T16:38:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/test_pipeline_execution_contract.py
summary: Replaced fragile __instancecheck__-based mocking with real ExecutionMetricsRunnerPort
  contract tests in test_pipeline_execution_contract.py, restoring the negative TypeError
  assertion without MagicMock magic-method errors.
---

# Episodic summary

## Task

- Title: Fix pipeline execution contract metrics runner test

## Outcome

- Replaced fragile __instancecheck__-based mocking with real ExecutionMetricsRunnerPort contract tests in test_pipeline_execution_contract.py, restoring the negative TypeError assertion without MagicMock magic-method errors.

## Lessons learned

- Replace with durable follow-up if needed
