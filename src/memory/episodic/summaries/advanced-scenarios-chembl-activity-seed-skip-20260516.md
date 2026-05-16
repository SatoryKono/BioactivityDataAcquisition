---
id: advanced-scenarios-chembl-activity-seed-skip-20260516
title: Skip advanced ChEMBL activity seed when Silver is absent
task_id: advanced-scenarios-chembl-activity-seed-skip-20260516
created_at: '2026-05-16T13:12:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Updated the advanced scenarios ChEMBL activity seed helper to skip when the
  current cassette/policy envelope does not materialize a Silver table, instead of
  failing setup. Direct probe confirmed no Silver output even at limit=100.
---

# Episodic summary

## Task

- Title: Skip advanced ChEMBL activity seed when Silver is absent

## Outcome

- Updated the advanced scenarios ChEMBL activity seed helper to skip when the current cassette/policy envelope does not materialize a Silver table, instead of failing setup. Direct probe confirmed no Silver output even at limit=100.

## Lessons learned

- Replace with durable follow-up if needed
