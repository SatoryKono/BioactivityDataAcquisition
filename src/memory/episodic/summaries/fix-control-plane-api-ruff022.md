---
id: fix-control-plane-api-ruff022
title: Fix unsorted __all__ in control_plane_api
task_id: fix-control-plane-api-ruff022
created_at: '2026-06-02T08:36:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/control_plane_api.py
summary: Sorted the control-plane API __all__ export list to clear RUF022, then regenerated
  module-coverage inventory source_tree_sha256 and revalidated the targeted architecture
  guards.
---

# Episodic summary

## Task

- Title: Fix unsorted __all__ in control_plane_api

## Outcome

- Sorted the control-plane API __all__ export list to clear RUF022, then regenerated module-coverage inventory source_tree_sha256 and revalidated the targeted architecture guards.

## Lessons learned

- Replace with durable follow-up if needed
