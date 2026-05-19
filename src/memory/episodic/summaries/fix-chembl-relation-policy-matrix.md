---
id: fix-chembl-relation-policy-matrix
title: Fix missing chembl_activity.relation policy matrix classification
task_id: fix-chembl-relation-policy-matrix
created_at: '2026-05-19T03:38:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/config/test_chembl_policy_surface_parity.py
summary: Updated the pipeline normalization matrix builder to emit reviewed alias
  rows in both directions for Silver/profile naming seams, which materializes chembl_activity.relation
  alongside activity_relation. Added regression assertions for the new relation row
  and regenerated committed pipeline normalization matrix artifacts. Verified with
  targeted ChemBL policy parity integration coverage and the full pipeline-normalization
  matrix unit suite.
---

# Episodic summary

## Task

- Title: Fix missing chembl_activity.relation policy matrix classification

## Outcome

- Updated the pipeline normalization matrix builder to emit reviewed alias rows in both directions for Silver/profile naming seams, which materializes chembl_activity.relation alongside activity_relation. Added regression assertions for the new relation row and regenerated committed pipeline normalization matrix artifacts. Verified with targeted ChemBL policy parity integration coverage and the full pipeline-normalization matrix unit suite.

## Lessons learned

- Replace with durable follow-up if needed
