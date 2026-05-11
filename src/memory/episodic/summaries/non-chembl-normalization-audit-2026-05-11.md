---
id: non-chembl-normalization-audit-2026-05-11
title: Audit non-ChEMBL normalization across BioETL
task_id: non-chembl-normalization-audit-2026-05-11
created_at: '2026-05-11T16:38:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md
summary: 'Audited non-ChEMBL normalization across publication, pubchem, and uniprot
  pipeline families on main using configs, normalization profiles, structured JSON
  policy, reference-id canonicalizers, composite configs, generated normalization
  matrix, and targeted non-ChEMBL contract/architecture tests. Main finding: publication
  normalization is the strongest shared layer; PubChem and UniProt have deterministic
  profile coverage and identifier canonicalization but thinner controlled-vocabulary
  externalization outside a few strict enums. Composite publication/molecule/target
  rely on normalized DOI/PMID/InChIKey/SMILES/UniProt anchors, so drift risk is concentrated
  in raw provider vocabularies and semantic-sensitive JSON payloads rather than in
  primary join-key canonicalization.'
---

# Episodic summary

## Task

- Title: Audit non-ChEMBL normalization across BioETL

## Outcome

- Audited non-ChEMBL normalization across publication, pubchem, and uniprot pipeline families on main using configs, normalization profiles, structured JSON policy, reference-id canonicalizers, composite configs, generated normalization matrix, and targeted non-ChEMBL contract/architecture tests. Main finding: publication normalization is the strongest shared layer; PubChem and UniProt have deterministic profile coverage and identifier canonicalization but thinner controlled-vocabulary externalization outside a few strict enums. Composite publication/molecule/target rely on normalized DOI/PMID/InChIKey/SMILES/UniProt anchors, so drift risk is concentrated in raw provider vocabularies and semantic-sensitive JSON payloads rather than in primary join-key canonicalization.

## Lessons learned

- Replace with durable follow-up if needed
