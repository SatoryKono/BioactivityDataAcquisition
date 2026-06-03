---
id: debug-run-all-timeout-20260603
title: Debug run_all CLI timeout in unit test
task_id: debug-run-all-timeout-20260603
created_at: '2026-06-03T16:39:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Fixed run_all service-mock test isolation by patching observability backend
  startup, metrics startup, and health server context across the whole test module.
  Manual CLI and direct async reproductions now complete without entering real composition
  bootstrap imports.
---

# Episodic summary

## Task

- Title: Debug run_all CLI timeout in unit test

## Outcome

- Fixed run_all service-mock test isolation by patching observability backend startup, metrics startup, and health server context across the whole test module. Manual CLI and direct async reproductions now complete without entering real composition bootstrap imports.

## Lessons learned

- Replace with durable follow-up if needed
