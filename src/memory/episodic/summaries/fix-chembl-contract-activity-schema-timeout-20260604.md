---
id: fix-chembl-contract-activity-schema-timeout-20260604
title: Fix ChEMBL contract activity schema timeout
task_id: fix-chembl-contract-activity-schema-timeout-20260604
created_at: '2026-06-04T12:38:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_chembl_contract.py::TestChemblContract::test_activity_endpoint_schema
summary: Bounded ChEMBL live contract requests with an internal per-attempt timeout
  and smaller retry delay/budget so transient provider latency or 5xx responses skip
  within the pytest async timeout instead of hanging for 60 seconds. Targeted live
  activity schema check now skip-returns on ChEMBL HTTP 500 instead of timing out;
  default non-live contract file remains offline-skipped.
---

# Episodic summary

## Task

- Title: Fix ChEMBL contract activity schema timeout

## Outcome

- Bounded ChEMBL live contract requests with an internal per-attempt timeout and smaller retry delay/budget so transient provider latency or 5xx responses skip within the pytest async timeout instead of hanging for 60 seconds. Targeted live activity schema check now skip-returns on ChEMBL HTTP 500 instead of timing out; default non-live contract file remains offline-skipped.

## Lessons learned

- Replace with durable follow-up if needed
