---
id: fix-chembl-contract-activity-schema-timeout-20260604
title: Fix ChEMBL contract activity schema timeout
task_id: fix-chembl-contract-activity-schema-timeout-20260604
created_at: '2026-06-04T12:36:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_chembl_contract.py::TestChemblContract::test_activity_endpoint_schema
summary: Active task session context.
query: test_chembl_contract activity_endpoint_schema _request_or_skip timeout ChEMBL
  contract VCR live skip
---

# Session note

## Task

- Title: Fix ChEMBL contract activity schema timeout
- Retrieval query: test_chembl_contract activity_endpoint_schema _request_or_skip timeout ChEMBL contract VCR live skip

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
