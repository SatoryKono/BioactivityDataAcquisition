---
id: chembl-contract-registry-hash
title: Fix chembl contract registry hash drift
task_id: chembl-contract-registry-hash
created_at: '2026-05-19T03:30:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/config/test_chembl_contract_registry_coverage.py
summary: Updated the shipped chembl.assay contract registry entry to the current normalization
  profile hash after assay profile/runtime changes and kept the normalization-matrix
  unit aligned with the current generated chembl_assay field surface.
---

# Episodic summary

## Task

- Title: Fix chembl contract registry hash drift

## Outcome

- Updated the shipped chembl.assay contract registry entry to the current normalization profile hash after assay profile/runtime changes and kept the normalization-matrix unit aligned with the current generated chembl_assay field surface.

## Lessons learned

- Replace with durable follow-up if needed
