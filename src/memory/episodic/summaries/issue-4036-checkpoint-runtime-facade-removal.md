---
id: issue-4036-checkpoint-runtime-facade-removal
title: Issue 4036 checkpoint runtime facade removal
task_id: issue-4036-checkpoint-runtime-facade-removal
created_at: '2026-05-13T17:09:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed checkpoint_compatibility_runtime.py, converted its architecture guard
  to a hard absence check, extended shared removed-facade guards, and passed targeted
  architecture pytest via the repo wrapper; refresh still requires skip-refresh because
  generated memory surfaces can lag removal waves.
---

# Episodic summary

## Task

- Title: Issue 4036 checkpoint runtime facade removal

## Outcome

- Removed checkpoint_compatibility_runtime.py, converted its architecture guard to a hard absence check, extended shared removed-facade guards, and passed targeted architecture pytest via the repo wrapper; refresh still requires skip-refresh because generated memory surfaces can lag removal waves.

## Lessons learned

- Replace with durable follow-up if needed
