---
id: technical-debt-github-issues
title: Prepare GitHub issues for technical debt audit findings
task_id: technical-debt-github-issues
created_at: '2026-05-25T12:07:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Created five non-duplicate GitHub issues from confirmed technical debt audit
  findings: #4651 architecture dependency map drift, #4652 deprecated composite service
  aliases, #4653 ChEMBL legacy field alias migration, #4654 classified zero-import
  burn-down, #4655 Delta write benchmark timeout isolation. Used GitHub REST API because
  gh CLI is unavailable in WSL; token was read from .env without printing secret values.
  Existing issues already cover coverage gates, live provider lanes, runtime/control-plane
  refactors, config-root runtime resolution, and retained entrypoint burden, so duplicates
  were not created.'
---

# Episodic summary

## Task

- Title: Prepare GitHub issues for technical debt audit findings

## Outcome

- Created five non-duplicate GitHub issues from confirmed technical debt audit findings: #4651 architecture dependency map drift, #4652 deprecated composite service aliases, #4653 ChEMBL legacy field alias migration, #4654 classified zero-import burn-down, #4655 Delta write benchmark timeout isolation. Used GitHub REST API because gh CLI is unavailable in WSL; token was read from .env without printing secret values. Existing issues already cover coverage gates, live provider lanes, runtime/control-plane refactors, config-root runtime resolution, and retained entrypoint burden, so duplicates were not created.

## Lessons learned

- Replace with durable follow-up if needed
