---
id: chembl-activity-canonical-original-values-fallback
title: Fix chembl_activity canonical original-value projection
task_id: chembl-activity-canonical-original-values-fallback
created_at: '2026-05-16T13:15:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/chembl/activity_transformer.py
summary: Projected canonical activity_type/activity_relation/activity_value before
  structural policy so chembl_activity seeds no longer fail when ChEMBL omits raw
  relation but supplies standardized values.
---

# Episodic summary

## Task

- Title: Fix chembl_activity canonical original-value projection

## Outcome

- Projected canonical activity_type/activity_relation/activity_value before structural policy so chembl_activity seeds no longer fail when ChEMBL omits raw relation but supplies standardized values.

## Lessons learned

- Replace with durable follow-up if needed
