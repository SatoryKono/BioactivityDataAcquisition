---
id: semantic-etl-refactor-next-2026-05-14
title: Continue semantic ETL refactor implementation
task_id: semantic-etl-refactor-next-2026-05-14
created_at: '2026-05-14T16:55:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/check_semantic_anchor_parity.py
summary: 'Extended semantic anchor parity gate to cover the remaining audit-recommended
  anchors: pmc_id, publication_id, target_id, canonical_smiles, uniprot_accession,
  and UniProt protein accession, while preserving stage-specific requiredness. The
  gate now checks entity DQ validations/filters/contracts, Gold requiredness/nullability,
  domain join-key normalization policy presence, and composite join/output/column-group
  anchors. Validation passed for direct/routed parity checks, ruff, py_compile, semantic
  anchor tests, join-key normalization tests, semantic field unification tests, docs
  forbidden-pattern scan for the touched doc, and import-boundary scan.'
---

# Episodic summary

## Task

- Title: Continue semantic ETL refactor implementation

## Outcome

- Extended semantic anchor parity gate to cover the remaining audit-recommended anchors: pmc_id, publication_id, target_id, canonical_smiles, uniprot_accession, and UniProt protein accession, while preserving stage-specific requiredness. The gate now checks entity DQ validations/filters/contracts, Gold requiredness/nullability, domain join-key normalization policy presence, and composite join/output/column-group anchors. Validation passed for direct/routed parity checks, ruff, py_compile, semantic anchor tests, join-key normalization tests, semantic field unification tests, docs forbidden-pattern scan for the touched doc, and import-boundary scan.

## Lessons learned

- Replace with durable follow-up if needed
