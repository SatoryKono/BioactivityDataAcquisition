---
id: chembl-target-nullability-fix
title: Fix chembl target protein classification nullability
task_id: chembl-target-nullability-fix
created_at: '2026-06-01T17:34:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Aligned chembl_target_protein_classification declared business/contract keys
  to entity_id so nullable component_id and leaf_id remain valid for missing_classification
  and quarantined rows.
---

# Episodic summary

## Task

- Title: Fix chembl target protein classification nullability

## Outcome

- Aligned chembl_target_protein_classification declared business/contract keys to entity_id so nullable component_id and leaf_id remain valid for missing_classification and quarantined rows.

## Lessons learned

- Replace with durable follow-up if needed
