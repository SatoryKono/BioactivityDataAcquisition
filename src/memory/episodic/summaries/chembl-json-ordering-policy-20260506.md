---
id: chembl-json-ordering-policy-20260506
title: Enforce one JSON ordering policy for ChEMBL hash canonicalization
task_id: chembl-json-ordering-policy-20260506
created_at: '2026-05-06T17:10:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/pipeline_normalizers.py
summary: Removed duplicate ChEMBL hash_policy.field_ordering config mirrors, enforced
  loader rejection of non-empty ChEMBL ordering mirrors, and anchored JSON ordering
  semantics solely in domain chembl_json_ordering_policy plus profile set_like_fields.
---

# Episodic summary

## Task

- Title: Enforce one JSON ordering policy for ChEMBL hash canonicalization

## Outcome

- Removed duplicate ChEMBL hash_policy.field_ordering config mirrors, enforced loader rejection of non-empty ChEMBL ordering mirrors, and anchored JSON ordering semantics solely in domain chembl_json_ordering_policy plus profile set_like_fields.

## Lessons learned

- Replace with durable follow-up if needed
