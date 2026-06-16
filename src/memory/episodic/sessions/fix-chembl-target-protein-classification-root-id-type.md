---
id: fix-chembl-target-protein-classification-root-id-type
title: Fix chembl target protein classification root_id schema type
task_id: fix-chembl-target-protein-classification-root-id-type
created_at: '2026-06-16T15:02:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/silver_schemas/test_field_types.py
summary: Active task session context.
query: chembl_target_protein_classification root_id Int64 Series string silver schema
  field types
---

# Session note

## Task

- Title: Fix chembl target protein classification root_id schema type
- Retrieval query: chembl_target_protein_classification root_id Int64 Series string silver schema field types

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- `chembl_target_protein_classification.root_id` failed the Silver schema ID-field contract because the schema exposed it as `Int64`.
- The fix keeps hierarchy internals numeric and converts `root_id` to text at the transformer/Silver schema boundary.
- Contract and unit validation passed after updating the schema snapshot and refreshing module coverage inventory.
