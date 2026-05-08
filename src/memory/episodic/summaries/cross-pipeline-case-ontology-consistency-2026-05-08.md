---
id: cross-pipeline-case-ontology-consistency-2026-05-08
title: Consolidate ChEMBL case and ontology consistency contracts
task_id: cross-pipeline-case-ontology-consistency-2026-05-08
created_at: '2026-05-08T14:16:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added a consolidated ChEMBL contract suite that locks shared case normalization
  across activity, assay, assay_parameters, molecule, target, and target_component
  families, validates ontology ID canonicalization across assay/cell_line/tissue,
  and asserts target remains non-ontology by design. Verified with targeted contract
  pytest subsets and import-order/compile checks.
---

# Episodic summary

## Task

- Title: Consolidate ChEMBL case and ontology consistency contracts

## Outcome

- Added a consolidated ChEMBL contract suite that locks shared case normalization across activity, assay, assay_parameters, molecule, target, and target_component families, validates ontology ID canonicalization across assay/cell_line/tissue, and asserts target remains non-ontology by design. Verified with targeted contract pytest subsets and import-order/compile checks.

## Lessons learned

- Replace with durable follow-up if needed
