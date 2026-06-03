---
id: chembl-adapter-config-resilience-fields
title: Fix ChEMBL adapter resilience config constructor drift
task_id: chembl-adapter-config-resilience-fields
created_at: '2026-06-03T07:22:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/test_chembl_paging_resilience.py
summary: Active task session context.
query: AdapterConfig retry_backoff_factor rate_limit_requests_per_second circuit_breaker_failure_threshold
  enable_single_id_fallback timeout Chembl
---

# Session note

## Task

- Title: Fix ChEMBL adapter resilience config constructor drift
- Retrieval query: AdapterConfig retry_backoff_factor rate_limit_requests_per_second circuit_breaker_failure_threshold enable_single_id_fallback timeout Chembl

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
