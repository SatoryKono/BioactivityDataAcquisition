---
id: issue-4036-execution-facade-removal
title: Issue 4036 execution facade removal wave
task_id: issue-4036-execution-facade-removal
created_at: '2026-05-13T16:28:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed six test-only execution facade modules from application.services,
  moved tests to canonical execution owners, converted the RunExecutionContext shim
  guard to an absence check, and passed targeted pytest via the repo wrapper; refresh
  still requires skip-refresh because generated memory surfaces can lag removal waves.
---

# Episodic summary

## Task

- Title: Issue 4036 execution facade removal wave

## Outcome

- Removed six test-only execution facade modules from application.services, moved tests to canonical execution owners, converted the RunExecutionContext shim guard to an absence check, and passed targeted pytest via the repo wrapper; refresh still requires skip-refresh because generated memory surfaces can lag removal waves.

## Lessons learned

- Replace with durable follow-up if needed
