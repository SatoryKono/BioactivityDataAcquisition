---
id: fix-semanticscholar-e2e-429
title: Stabilize Semantic Scholar E2E under rate limiting
task_id: fix-semanticscholar-e2e-429
created_at: '2026-06-03T17:56:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/conftest.py
summary: Updated E2E transient handling so RetryExhaustedError with nested transient
  429/5xx last_error is treated as a deterministic upstream skip instead of a hard
  failure, and added regression coverage for the immediate-skip path.
---

# Episodic summary

## Task

- Title: Stabilize Semantic Scholar E2E under rate limiting

## Outcome

- Updated E2E transient handling so RetryExhaustedError with nested transient 429/5xx last_error is treated as a deterministic upstream skip instead of a hard failure, and added regression coverage for the immediate-skip path.

## Lessons learned

- Replace with durable follow-up if needed
