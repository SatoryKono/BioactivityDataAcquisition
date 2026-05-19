---
id: fix-chembl-assay-contract-registry-hash
title: Refresh chembl.assay normalization hash in contract registry
task_id: FIX-CHEMBL-ASSAY-CONTRACT-REGISTRY-HASH
created_at: '2026-05-19T04:56:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated stale chembl.assay normalization_profile_hash in contract_registry.yaml
  to match the current chembl.assay normalization profile after canonical assay_description
  rename. Verified with chembl contract registry coverage test and contract identity
  CI validator.
---

# Episodic summary

## Task

- Title: Refresh chembl.assay normalization hash in contract registry

## Outcome

- Updated stale chembl.assay normalization_profile_hash in contract_registry.yaml to match the current chembl.assay normalization profile after canonical assay_description rename. Verified with chembl contract registry coverage test and contract identity CI validator.

## Lessons learned

- Replace with durable follow-up if needed
