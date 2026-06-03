---
id: asyncio-timeout-idle-loop-debug
title: Debug pytest asyncio idle-loop timeout
task_id: asyncio-timeout-idle-loop-debug
created_at: '2026-06-03T08:39:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_pipeline_matrix_e2e.py
summary: Added an internal asyncio.wait_for guard around pipeline matrix smoke execution
  so pytest-timeout idle-loop hangs surface as deterministic E2E_FAIL[PIPELINE_EXECUTION_TIMEOUT]
  diagnostics with pipeline and run_id; validated ruff, targeted matrix skip, e2e
  policy checks, and test-governance drift guard.
---

# Episodic summary

## Task

- Title: Debug pytest asyncio idle-loop timeout

## Outcome

- Added an internal asyncio.wait_for guard around pipeline matrix smoke execution so pytest-timeout idle-loop hangs surface as deterministic E2E_FAIL[PIPELINE_EXECUTION_TIMEOUT] diagnostics with pipeline and run_id; validated ruff, targeted matrix skip, e2e policy checks, and test-governance drift guard.

## Lessons learned

- Replace with durable follow-up if needed
