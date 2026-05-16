---
id: chembl-assay-parameters-operator-fix-20260516
title: Fix ChEMBL assay parameter relation operator normalization
task_id: chembl-assay-parameters-operator-fix-20260516
created_at: '2026-05-16T12:55:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py
summary: Mapped assay parameter relation and parameter_relation to operator normalization
  so Unicode relation symbols canonicalize to ASCII comparison operators.
---

# Episodic summary

## Task

- Title: Fix ChEMBL assay parameter relation operator normalization

## Outcome

- Mapped assay parameter relation and parameter_relation to operator normalization so Unicode relation symbols canonicalize to ASCII comparison operators.

## Lessons learned

- Replace with durable follow-up if needed
