---
id: chembl-contract-target-live-500-20260524
title: Fix ChEMBL target live contract 500
task_id: chembl-contract-target-live-500-20260524
created_at: '2026-05-24T17:58:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_chembl_contract.py
summary: Stabilized the ChEMBL target live contract probe by filtering target.json
  to the known CHEMBL1824 target. Unfiltered target.json?limit=1 currently returns
  an upstream EBI 500 HTML page, while the filtered paginated target endpoint and
  direct target lookup return 200 JSON. Verified target schema/snapshot tests and
  the full live ChEMBL contract file.
---

# Episodic summary

## Task

- Title: Fix ChEMBL target live contract 500

## Outcome

- Stabilized the ChEMBL target live contract probe by filtering target.json to the known CHEMBL1824 target. Unfiltered target.json?limit=1 currently returns an upstream EBI 500 HTML page, while the filtered paginated target endpoint and direct target lookup return 200 JSON. Verified target schema/snapshot tests and the full live ChEMBL contract file.

## Lessons learned

- Replace with durable follow-up if needed
