---
id: fix-type-checking-density-composition-factories
title: Reduce TYPE_CHECKING density in composition factories
task_id: fix-type-checking-density-composition-factories
created_at: '2026-05-24T17:37:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_type_checking_density.py
summary: Removed five TYPE_CHECKING blocks from composition factory hotspot modules
  by promoting type imports to module level; architecture density test now passes.
---

# Episodic summary

## Task

- Title: Reduce TYPE_CHECKING density in composition factories

## Outcome

- Removed five TYPE_CHECKING blocks from composition factory hotspot modules by promoting type imports to module level; architecture density test now passes.

## Lessons learned

- Replace with durable follow-up if needed
