---
id: chembl-target-field-order-20260601
title: Fix transformer snapshot registry drift
task_id: chembl-target-field-order-20260601
created_at: '2026-06-01T14:14:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/pipelines/__snapshots__/test_transformer_snapshots.ambr
summary: Updated transformer snapshot registry keys to match renamed hashed test names
  and refreshed the single TargetTransformer snapshot entry to include shipped target_protein_class_L1-L5
  null fields; verified tests/unit/application/pipelines/test_transformer_snapshots.py
  passes with 10 snapshots.
---

# Episodic summary

## Task

- Title: Fix transformer snapshot registry drift

## Outcome

- Updated transformer snapshot registry keys to match renamed hashed test names and refreshed the single TargetTransformer snapshot entry to include shipped target_protein_class_L1-L5 null fields; verified tests/unit/application/pipelines/test_transformer_snapshots.py passes with 10 snapshots.

## Lessons learned

- Replace with durable follow-up if needed
