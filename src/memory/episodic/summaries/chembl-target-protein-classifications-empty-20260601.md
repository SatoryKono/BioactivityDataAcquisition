---
id: chembl-target-protein-classifications-empty-20260601
title: Diagnose empty chembl_target protein_classifications
task_id: chembl-target-protein-classifications-empty-20260601
created_at: '2026-06-01T08:51:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/chembl/target_transformer.py
summary: 'Diagnosed chembl_target protein classification behavior: standalone chembl_target
  reads /target payloads only and projects protein_classifications solely from target_components[*].protein_classifications,
  which the target endpoint does not provide. L1-L5 hierarchy fields exist only on
  the separate chembl_target_protein_classification relation schema as l1_id..l5_id;
  no target_protein_class_id_L1..L5 fields are declared or merged into chembl_target.'
---

# Episodic summary

## Task

- Title: Diagnose empty chembl_target protein_classifications

## Outcome

- Diagnosed chembl_target protein classification behavior: standalone chembl_target reads /target payloads only and projects protein_classifications solely from target_components[*].protein_classifications, which the target endpoint does not provide. L1-L5 hierarchy fields exist only on the separate chembl_target_protein_classification relation schema as l1_id..l5_id; no target_protein_class_id_L1..L5 fields are declared or merged into chembl_target.

## Lessons learned

- Replace with durable follow-up if needed
