---
id: fix-chembl-target-protein-classification-root-id-type
title: Fix chembl target protein classification root_id schema type
task_id: fix-chembl-target-protein-classification-root-id-type
created_at: '2026-06-16T15:23:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/silver_schemas/test_field_types.py
- src/bioetl/domain/schemas/chembl/target_protein_classification.py
- src/bioetl/application/pipelines/chembl/target_protein_classification_transformer.py
- src/bioetl/domain/normalization/profiles/chembl_target_protein_classification.py
summary: Fixed Silver schema contract failure by publishing chembl_target_protein_classification
  root_id as string at the transformer/Silver schema boundary, updating normalization
  profile and Silver schema snapshot, and refreshing module coverage inventory.
---

# Episodic summary

## Task

- Title: Fix chembl target protein classification root_id schema type

## Outcome

- Fixed Silver schema contract failure by publishing chembl_target_protein_classification root_id as string at the transformer/Silver schema boundary, updating normalization profile and Silver schema snapshot, and refreshing module coverage inventory.

## Lessons learned

- Silver ID-field governance applies to `root_id` even when upstream ChEMBL hierarchy values are numeric; boundary transformers should publish such identifiers as strings.
