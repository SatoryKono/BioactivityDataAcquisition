---
id: hooks-check-20260616
title: Check project hooks
task_id: hooks-check-20260616
created_at: '2026-06-16T07:07:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- .pre-commit-config.yaml
summary: Audited project hook installation and execution. Found local checkout hook
  drift, broken Makefile precommit-install dependency on system python, bandit pre-push
  environment install conflict, and commit-msg behavior mismatch.
---

# Episodic summary

## Task

- Title: Check project hooks

## Outcome

- Audited project hook installation and execution. Found local checkout hook drift, broken Makefile precommit-install dependency on system python, bandit pre-push environment install conflict, and commit-msg behavior mismatch.

## Lessons learned

- Replace with durable follow-up if needed
