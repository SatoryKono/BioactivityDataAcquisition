---
id: chembl-publication-similarity-doc-id-transform-failure
title: Fix ChEMBL publication similarity doc id transform failure
task_id: chembl-publication-similarity-doc-id-transform-failure
created_at: '2026-06-03T08:28:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py
summary: Fixed ChEMBL publication_similarity transformer to normalize provider-native
  document_1_chembl_id/document_2_chembl_id values into canonical numeric doc_1/doc_2,
  preserving deterministic composite sim_id generation. Added unit coverage for provider-native
  ChEMBL IDs and refreshed source-dependent governance artifacts. Targeted transformer,
  fixture/model, ruff, module coverage, dependency drift, test-governance, and file-size
  checks passed. E2E single-case could not reach pipeline execution in this checkout
  because unrelated observability dirty-tree split is missing _metrics_defs_adapter.
---

# Episodic summary

## Task

- Title: Fix ChEMBL publication similarity doc id transform failure

## Outcome

- Fixed ChEMBL publication_similarity transformer to normalize provider-native document_1_chembl_id/document_2_chembl_id values into canonical numeric doc_1/doc_2, preserving deterministic composite sim_id generation. Added unit coverage for provider-native ChEMBL IDs and refreshed source-dependent governance artifacts. Targeted transformer, fixture/model, ruff, module coverage, dependency drift, test-governance, and file-size checks passed. E2E single-case could not reach pipeline execution in this checkout because unrelated observability dirty-tree split is missing _metrics_defs_adapter.

## Lessons learned

- Replace with durable follow-up if needed
