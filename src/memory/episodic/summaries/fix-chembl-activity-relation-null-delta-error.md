---
id: fix-chembl-activity-relation-null-delta-error
title: Fix chembl activity relation null Delta write error
task_id: fix-chembl-activity-relation-null-delta-error
created_at: '2026-05-19T03:52:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Canonicalized chembl activity raw measurement fields at the entity and transformer
  layers so Silver uses activity_type/activity_relation/activity_value before entity
  construction; this removed legacy type/value/relation leakage into Delta writes
  and restored chembl_activity integration plus rollout e2e coverage.
---

# Episodic summary

## Task

- Title: Fix chembl activity relation null Delta write error

## Outcome

- Canonicalized chembl activity raw measurement fields at the entity and transformer layers so Silver uses activity_type/activity_relation/activity_value before entity construction; this removed legacy type/value/relation leakage into Delta writes and restored chembl_activity integration plus rollout e2e coverage.

## Lessons learned

- Replace with durable follow-up if needed
