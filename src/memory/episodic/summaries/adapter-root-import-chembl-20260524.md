---
id: adapter-root-import-chembl-20260524
title: Fix ChEMBL adapter package-root import architecture failure
task_id: adapter-root-import-chembl-20260524
created_at: '2026-05-24T17:45:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/extraction_params_support.py
summary: Replaced direct ChemblAdapter imports from bioetl.infrastructure.adapters.chembl.client
  in the ChEMBL extraction-params integration helper with the provider package-root
  facade. Verified the failing adapter contract test, full adapter contract architecture
  file, and ChEMBL extraction-params integration subset.
---

# Episodic summary

## Task

- Title: Fix ChEMBL adapter package-root import architecture failure

## Outcome

- Replaced direct ChemblAdapter imports from bioetl.infrastructure.adapters.chembl.client in the ChEMBL extraction-params integration helper with the provider package-root facade. Verified the failing adapter contract test, full adapter contract architecture file, and ChEMBL extraction-params integration subset.

## Lessons learned

- Replace with durable follow-up if needed
