---
id: fix-chembl-contract-registry-hash
title: Fix ChEMBL contract registry coverage hash drift
task_id: fix-chembl-contract-registry-hash
created_at: '2026-05-31T15:00:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/base/contract_registry.yaml
summary: Synced chembl.target normalization_profile_hash in configs/base/contract_registry.yaml
  back to the canonical source identity 746da0091c51435886d320b4582aae8f0b1701abf37885a045183d4bb125ff5c
  reported by resolve_normalization_profile_identity and the generated Gold contract.
  Verified the ChEMBL contract registry integration suite, registry validator, config
  validation, and diff whitespace check.
---

# Episodic summary

## Task

- Title: Fix ChEMBL contract registry coverage hash drift

## Outcome

- Synced chembl.target normalization_profile_hash in configs/base/contract_registry.yaml back to the canonical source identity 746da0091c51435886d320b4582aae8f0b1701abf37885a045183d4bb125ff5c reported by resolve_normalization_profile_identity and the generated Gold contract. Verified the ChEMBL contract registry integration suite, registry validator, config validation, and diff whitespace check.

## Lessons learned

- Replace with durable follow-up if needed
