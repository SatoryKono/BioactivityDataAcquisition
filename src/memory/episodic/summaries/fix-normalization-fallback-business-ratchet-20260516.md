---
id: fix-normalization-fallback-business-ratchet-20260516
title: Fix normalization fallback business ratchet failures
task_id: fix-normalization-fallback-business-ratchet-20260516
created_at: '2026-05-16T09:25:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/normalization/profiles/base.py
- src/bioetl/domain/normalization/profiles/chembl_activity.py
- src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py
- scripts/docs/matrix/generate_pipeline_normalization_matrix.py
- configs/base/contract_registry.yaml
- configs/entities/chembl/assay.yaml
- tests/unit/domain/normalization/profiles/test_chembl_activity.py
- tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py
summary: Restored published ChEMBL normalization surfaces for generic Silver field
  names via alias-aware profile lookup, rolled matrix output back to Silver field
  names, removed duplicate chembl_assay hash-policy field, and synced contract registry
  profile hashes for affected ChEMBL profiles.
---

# Episodic summary

## Task

- Title: Fix normalization fallback business ratchet failures

## Outcome

- Restored published ChEMBL normalization surfaces for generic Silver field names via alias-aware profile lookup, rolled matrix output back to Silver field names, removed duplicate chembl_assay hash-policy field, and synced contract registry profile hashes for affected ChEMBL profiles.

## Lessons learned

- Replace with durable follow-up if needed
