---
id: fix-chembl-oa-status-diamond
title: Fix ChEMBL oa_status enum parity
task_id: fix-chembl-oa-status-diamond
created_at: '2026-06-04T07:24:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/publication.yaml
- tests/integration/config/test_chembl_enum_parity.py
summary: Verified chembl_publication.oa_status quality allowed values include diamond
  and match publication.oa_status_values; targeted parity test file passes.
---

# Episodic summary

## Task

- Title: Fix ChEMBL oa_status enum parity

## Outcome

- Verified chembl_publication.oa_status quality allowed values include diamond and match publication.oa_status_values; targeted parity test file passes.

## Lessons learned

- Replace with durable follow-up if needed
