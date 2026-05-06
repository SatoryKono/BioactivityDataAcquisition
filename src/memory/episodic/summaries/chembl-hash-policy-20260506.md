---
id: chembl-hash-policy-20260506
title: Consolidate ChEMBL content-hash policy source
task_id: chembl-hash-policy-20260506
created_at: '2026-05-06T15:07:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/activity.yaml
- src/bioetl/infrastructure/config/pipeline_normalizers.py
- src/bioetl/composition/factories/pipeline/transformer_builder.py
- src/bioetl/application/core/_record_normalization_hash_support.py
summary: Added a typed authoritative content-hash policy loaded from root hash_policy,
  validated legacy schema/contracts hash shims as empty when present, and switched
  ChEMBL runtime hashing to prefer the authoritative policy over contract/profile
  hash field selection.
---

# Episodic summary

## Task

- Title: Consolidate ChEMBL content-hash policy source

## Outcome

- Added a typed authoritative content-hash policy loaded from root hash_policy, validated legacy schema/contracts hash shims as empty when present, and switched ChEMBL runtime hashing to prefer the authoritative policy over contract/profile hash field selection.

## Lessons learned

- Replace with durable follow-up if needed
