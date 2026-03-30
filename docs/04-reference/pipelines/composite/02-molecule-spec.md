---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Composite Molecule Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/molecule.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `composite_molecule` |
| Provider | `composite` |
| Entity | `molecule` |
| Seed Pipeline | `chembl_molecule` |
| Enrichers | `pubchem_compound` |
| Join Keys | `inchi_key`, fallback `canonical_smiles` |
| Conflict Resolution | `seed_priority` |
| Preserve All Sources | `true` |
| Silver Output | `data/output/silver/composite/molecule` |
| Gold Output | `data/output/gold/composite/molecule` |

## Notes

- Current contract uses snake_case field names such as `molecule_id`,
  `inchi_key`, `canonical_smiles`, `pref_name`, `molecular_weight`,
  `standard_inchi`.
- Canonical field aliasing between ChEMBL and PubChem is maintained in the
  composite YAML config; this page no longer republishes the older dashed join
  notes.
- For merge priorities, field aliases, and output groups, use the composite
  YAML config above.
