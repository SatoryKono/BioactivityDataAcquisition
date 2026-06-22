---
id: debug-chembl-target-component-contract-hash-include
title: Fix ChEMBL target_component contract hash_include validation
task_id: debug-chembl-target-component-contract-hash-include
created_at: '2026-06-22T16:10:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/target_component.yaml
summary: Investigated reported ChEMBL target_component failure for contracts.hash_include
  with root hash_policy. Current checkout has empty contracts.hash_include/hash_exclude,
  base contract_defaults.hash_include is empty, config validation passes, and the
  targeted integration test passes in both WSL and Windows .venv-win. No source/config
  fix was needed; likely the reported failure came from a stale pre-refresh config/test
  run.
---

# Episodic summary

## Task

- Title: Fix ChEMBL target_component contract hash_include validation

## Outcome

- Investigated reported ChEMBL target_component failure for contracts.hash_include with root hash_policy. Current checkout has empty contracts.hash_include/hash_exclude, base contract_defaults.hash_include is empty, config validation passes, and the targeted integration test passes in both WSL and Windows .venv-win. No source/config fix was needed; likely the reported failure came from a stale pre-refresh config/test run.

## Lessons learned

- Replace with durable follow-up if needed
