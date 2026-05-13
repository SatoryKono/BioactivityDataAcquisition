---
id: issue-4036-pipeline-runner-facade-removal
title: Issue 4036 pipeline runner facade removal
task_id: issue-4036-pipeline-runner-facade-removal
created_at: '2026-05-13T16:55:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed pipeline_runner_service.py from application.services, moved tests
  and debug TYPE_CHECKING imports to canonical execution owners, updated active architecture/doc
  references, and passed targeted pytest via the repo wrapper; refresh still requires
  skip-refresh because generated memory surfaces can lag removal waves.
---

# Episodic summary

## Task

- Title: Issue 4036 pipeline runner facade removal

## Outcome

- Removed pipeline_runner_service.py from application.services, moved tests and debug TYPE_CHECKING imports to canonical execution owners, updated active architecture/doc references, and passed targeted pytest via the repo wrapper; refresh still requires skip-refresh because generated memory surfaces can lag removal waves.

## Lessons learned

- Replace with durable follow-up if needed
