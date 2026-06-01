---
id: chembl-target-protein-class-empty-20260601
title: Investigate empty protein classification fields in chembl_target
task_id: chembl-target-protein-class-empty-20260601
created_at: '2026-06-01T13:00:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Confirmed chembl_target leaves flattened target_protein_class_L1-L5 fields
  empty by design in transformer, while standalone protein_classifications depends
  on nested target_components payload that current target cassette does not provide;
  flattened hierarchy is populated via chembl_target_protein_classification summary
  in composite_target.
---

# Episodic summary

## Task

- Title: Investigate empty protein classification fields in chembl_target

## Outcome

- Confirmed chembl_target leaves flattened target_protein_class_L1-L5 fields empty by design in transformer, while standalone protein_classifications depends on nested target_components payload that current target cassette does not provide; flattened hierarchy is populated via chembl_target_protein_classification summary in composite_target.

## Lessons learned

- Replace with durable follow-up if needed
