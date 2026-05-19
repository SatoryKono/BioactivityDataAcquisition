---
id: test-governance-budget-sync
title: Sync static test governance budget after markerless drift
task_id: test-governance-budget-sync
created_at: '2026-05-19T10:27:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_reproducibility_golden_fixtures.py
summary: Reduced markerless test and uuid4 governance drift by marking reproducibility
  golden fixture tests as unit tests and replacing two nondeterministic uuid4 test
  IDs with fixed UUID constants.
---

# Episodic summary

## Task

- Title: Sync static test governance budget after markerless drift

## Outcome

- Reduced markerless test and uuid4 governance drift by marking reproducibility golden fixture tests as unit tests and replacing two nondeterministic uuid4 test IDs with fixed UUID constants.

## Lessons learned

- Replace with durable follow-up if needed
