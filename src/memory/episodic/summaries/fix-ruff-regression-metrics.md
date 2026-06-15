---
id: fix-ruff-regression-metrics
title: Fix ruff regression metrics failures
task_id: fix-ruff-regression-metrics
created_at: '2026-06-15T10:04:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/entities/__init__.py
summary: Cleared the ruff regression budget failure by shortening the domain context
  module docstring and converting domain entity TYPE_CHECKING re-export imports to
  redundant aliases, then refreshed module coverage inventory for the touched src
  tree.
---

# Episodic summary

## Task

- Title: Fix ruff regression metrics failures

## Outcome

- Cleared the ruff regression budget failure by shortening the domain context module docstring and converting domain entity TYPE_CHECKING re-export imports to redundant aliases, then refreshed module coverage inventory for the touched src tree.

## Lessons learned

- Replace with durable follow-up if needed
