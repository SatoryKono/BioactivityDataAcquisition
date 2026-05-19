---
id: fix-chembl-policy-surface-parity-failures
title: Fix current chembl policy surface parity failures
task_id: fix-chembl-policy-surface-parity-failures
created_at: '2026-05-19T11:53:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/chembl_policy_registry_loader.py
- tests/unit/infrastructure/config/test_chembl_policy_registry_loader.py
- tests/integration/config/test_chembl_policy_surface_parity.py
- docs/04-reference/schemas/domain/chembl/ontology-governance.md
summary: Updated ChemblPolicyRegistryLoader to merge unit_companion_policies into
  ontology families so config-backed UO/QUDT assay-parameter companion fields match
  default registry and matrix source attribution. Added unit regression test for loader
  and refreshed ontology governance doc to reflect optional assay-parameter UO/QUDT
  companion bundle. Verified parity, config, contract, and chembl_assay full-cycle
  E2E tests.
---

# Episodic summary

## Task

- Title: Fix current chembl policy surface parity failures

## Outcome

- Updated ChemblPolicyRegistryLoader to merge unit_companion_policies into ontology families so config-backed UO/QUDT assay-parameter companion fields match default registry and matrix source attribution. Added unit regression test for loader and refreshed ontology governance doc to reflect optional assay-parameter UO/QUDT companion bundle. Verified parity, config, contract, and chembl_assay full-cycle E2E tests.

## Lessons learned

- Replace with durable follow-up if needed
