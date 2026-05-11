---
id: explain-chembl-target-schema-error
title: Fix chembl_target downgraded schema mismatch
task_id: explain-chembl-target-schema-error
created_at: '2026-05-11T15:02:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/schemas/chembl/target.py
summary: 'Identified the chembl_target failure as a Silver Pandera schema mismatch
  on downgraded: pandas nullable boolean was rejected by TargetSchema expecting bool.
  Fixed the schema to use pd.BooleanDtype for downgraded and added a regression test
  covering batches with downgraded=True/None.'
---

# Episodic summary

## Task

- Title: Fix chembl_target downgraded schema mismatch

## Outcome

- Identified the chembl_target failure as a Silver Pandera schema mismatch on downgraded: pandas nullable boolean was rejected by TargetSchema expecting bool. Fixed the schema to use pd.BooleanDtype for downgraded and added a regression test covering batches with downgraded=True/None.

## Lessons learned

- Replace with durable follow-up if needed
