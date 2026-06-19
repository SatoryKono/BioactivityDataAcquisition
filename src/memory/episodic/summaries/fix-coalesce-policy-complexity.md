---
id: fix-coalesce-policy-complexity
title: Reduce coalesce policy complexity for architecture gate
task_id: fix-coalesce-policy-complexity
created_at: '2026-06-19T10:04:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/composite/coalesce_policy.py
summary: Refactored src/bioetl/application/composite/coalesce_policy.py to split latest-timestamp
  coalescing into smaller pure helpers, reducing cyclomatic complexity for application
  metrics gate while preserving behavior. Validated with targeted unit tests, application
  complexity gate, and direct module-coverage-inventory hash match; architecture inventory
  hash guard skipped on WSL.
---

# Episodic summary

## Task

- Title: Reduce coalesce policy complexity for architecture gate

## Outcome

- Refactored src/bioetl/application/composite/coalesce_policy.py to split latest-timestamp coalescing into smaller pure helpers, reducing cyclomatic complexity for application metrics gate while preserving behavior. Validated with targeted unit tests, application complexity gate, and direct module-coverage-inventory hash match; architecture inventory hash guard skipped on WSL.

## Lessons learned

- Replace with durable follow-up if needed
