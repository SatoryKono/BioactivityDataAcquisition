---
id: fix-chembl-contract-registry-hash-20260616
title: Fix ChEMBL target protein classification registry hash drift
task_id: fix-chembl-contract-registry-hash-20260616
created_at: '2026-06-16T16:59:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/base/contract_registry.yaml tests/integration/config/test_chembl_contract_registry_coverage.py
summary: Synced chembl.target_protein_classification normalization_profile_hash in
  configs/base/contract_registry.yaml to the live normalization profile identity 99e381173fbae0e1e436ca4e95ef4c9730ab318742543bf8b6678be3e2c37df0.
  The failing test_chembl_contract_registry_covers_all_shipped_gold_surfaces now passes,
  as do the full ChEMBL contract registry integration file, registry validator unit
  tests, and direct contract registry validator.
---

# Episodic summary

## Task

- Title: Fix ChEMBL target protein classification registry hash drift

## Outcome

- Synced chembl.target_protein_classification normalization_profile_hash in configs/base/contract_registry.yaml to the live normalization profile identity 99e381173fbae0e1e436ca4e95ef4c9730ab318742543bf8b6678be3e2c37df0. The failing test_chembl_contract_registry_covers_all_shipped_gold_surfaces now passes, as do the full ChEMBL contract registry integration file, registry validator unit tests, and direct contract registry validator.

## Lessons learned

- Replace with durable follow-up if needed
