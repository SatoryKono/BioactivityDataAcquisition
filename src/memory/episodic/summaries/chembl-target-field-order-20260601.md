---
id: chembl-target-field-order-20260601
title: Fix ChemblTargetSchema reviewed field order drift
task_id: chembl-target-field-order-20260601
created_at: '2026-06-01T14:05:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/infrastructure/schemas/test_silver.py
summary: Updated the Chembl target Silver schema unit test reviewed business-field
  order to include shipped target_protein_class_L1-L5 fields already present in configs/entities/chembl/target.yaml
  and CHEMBL_TARGET_SCHEMA; verified the failing targeted pytest now passes.
---

# Episodic summary

## Task

- Title: Fix ChemblTargetSchema reviewed field order drift

## Outcome

- Updated the Chembl target Silver schema unit test reviewed business-field order to include shipped target_protein_class_L1-L5 fields already present in configs/entities/chembl/target.yaml and CHEMBL_TARGET_SCHEMA; verified the failing targeted pytest now passes.

## Lessons learned

- Replace with durable follow-up if needed
