---
id: fix-target-protein-classification-class-size
title: Fix TargetProteinClassificationSnapshotDataSource class size metric
task_id: fix-target-protein-classification-class-size
created_at: '2026-06-16T15:25:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/providers/_chembl_target_protein_classification_data_source.py
summary: 'Fixed architecture code metrics failure by splitting TargetProteinClassificationSnapshotDataSource
  responsibilities: moved source manifest/fingerprint helpers into a private manifest
  module and target/component index filtering into the existing provider helper module.
  Class span is now 268 lines and provider data source file is 300 LOC. Added manifest
  helper tests and refreshed module coverage inventory/architecture scorecard without
  increasing unmeasured module count.'
---

# Episodic summary

## Task

- Title: Fix TargetProteinClassificationSnapshotDataSource class size metric

## Outcome

- Fixed architecture code metrics failure by splitting TargetProteinClassificationSnapshotDataSource responsibilities: moved source manifest/fingerprint helpers into a private manifest module and target/component index filtering into the existing provider helper module. Class span is now 268 lines and provider data source file is 300 LOC. Added manifest helper tests and refreshed module coverage inventory/architecture scorecard without increasing unmeasured module count.

## Lessons learned

- Replace with durable follow-up if needed
