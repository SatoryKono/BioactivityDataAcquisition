---
id: fix-ruff-f401-registry
title: Fix registry.py F401 ruff regression
task_id: fix-ruff-f401-registry
created_at: '2026-06-15T15:44:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed the dead GenericPipelineFactory type-only import from registry.py,
  cleared the ruff F401 regression, refreshed module-coverage-inventory.json after
  the src change, and verified the targeted architecture checks pass with the WSL
  source-tree hash guard still skipped by policy.
---

# Episodic summary

## Task

- Title: Fix registry.py F401 ruff regression

## Outcome

- Removed the dead GenericPipelineFactory type-only import from registry.py, cleared the ruff F401 regression, refreshed module-coverage-inventory.json after the src change, and verified the targeted architecture checks pass with the WSL source-tree hash guard still skipped by policy.

## Lessons learned

- Replace with durable follow-up if needed
