---
id: fix-oversized-test-module-inventory-20260525
title: Fix oversized test module inventory
task_id: fix-oversized-test-module-inventory-20260525
created_at: '2026-05-25T13:47:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/test_governance_audit.yaml
- configs/quality/pytest_shards.yaml
summary: Synced oversized test module governance inventory with current split test
  files, refreshed completed split line counts, and removed stale pytest shard ignore
  for removed test_runner_builder.py.
---

# Episodic summary

## Task

- Title: Fix oversized test module inventory

## Outcome

- Synced oversized test module governance inventory with current split test files, refreshed completed split line counts, and removed stale pytest shard ignore for removed test_runner_builder.py.

## Lessons learned

- Test governance inventories must be refreshed after splitting or removing
  oversized test modules; stale source paths also need removal from shard
  ignore lists.
