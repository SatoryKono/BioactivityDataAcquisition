---
id: fix-runner-request-compat-runcontext
title: Fix runner request compat RunContext regression
task_id: fix-runner-request-compat-runcontext
created_at: '2026-05-21T10:15:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/factories/pipeline/test_runner_request_compat.py
summary: 'Updated runner-request compatibility tests to use the current sanctioned
  minimal contracts: a runtime-like object instead of direct partial RunContext construction,
  and CachedBronzeContext.disabled() instead of the retired constructor shape.'
---

# Episodic summary

## Task

- Title: Fix runner request compat RunContext regression

## Outcome

- Updated runner-request compatibility tests to use the current sanctioned minimal contracts: a runtime-like object instead of direct partial RunContext construction, and CachedBronzeContext.disabled() instead of the retired constructor shape.

## Lessons learned

- Replace with durable follow-up if needed
