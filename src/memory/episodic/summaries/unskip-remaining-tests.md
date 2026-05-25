---
id: unskip-remaining-tests
title: Unskip remaining tests and fix runtime blockers
task_id: unskip-remaining-tests
created_at: '2026-05-25T03:33:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed memory.tooling.workflow help-path timeout by removing heavy top-level
  imports from src/memory/tooling/workflow.py and deferring memory query/refresh imports
  until command execution. The targeted memory tooling tests now pass.
---

# Episodic summary

## Task

- Title: Unskip remaining tests and fix runtime blockers

## Outcome

- Fixed memory.tooling.workflow help-path timeout by removing heavy top-level imports from src/memory/tooling/workflow.py and deferring memory query/refresh imports until command execution. The targeted memory tooling tests now pass.

## Lessons learned

- Replace with durable follow-up if needed
