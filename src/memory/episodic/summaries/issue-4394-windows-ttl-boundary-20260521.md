---
id: issue-4394-windows-ttl-boundary-20260521
title: Fix Windows TTL boundary in cleanup_repository test
task_id: issue-4394-windows-ttl-boundary-20260521
created_at: '2026-05-21T09:37:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Made reports/quality TTL age computation calendar-day based instead of full
  24-hour intervals so pretest_guardrails expiry is deterministic across Windows/Linux
  runners and does not depend on UTC hour-of-day. Validated the failing cleanup_repository
  test and py_compile.
---

# Episodic summary

## Task

- Title: Fix Windows TTL boundary in cleanup_repository test

## Outcome

- Made reports/quality TTL age computation calendar-day based instead of full 24-hour intervals so pretest_guardrails expiry is deterministic across Windows/Linux runners and does not depend on UTC hour-of-day. Validated the failing cleanup_repository test and py_compile.

## Lessons learned

- Replace with durable follow-up if needed
