---
id: record-chembl-paging-vcr
title: Record missing ChEMBL paging VCR cassettes
task_id: record-chembl-paging-vcr
created_at: '2026-06-15T11:52:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/test_chembl_paging_resilience.py
summary: Validated missing ChEMBL paging VCR recording path. Recording is blocked
  by live ChEMBL endpoint timeouts/500 responses on canonical activity and molecule
  resources; no cassette or catalog changes applied.
---

# Episodic summary

## Task

- Title: Record missing ChEMBL paging VCR cassettes

## Outcome

- Validated missing ChEMBL paging VCR recording path. Recording is blocked by live ChEMBL endpoint timeouts/500 responses on canonical activity and molecule resources; no cassette or catalog changes applied.

## Lessons learned

- Replace with durable follow-up if needed
