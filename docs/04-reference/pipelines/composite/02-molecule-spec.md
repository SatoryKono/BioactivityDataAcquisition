______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Composite Molecule Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/molecule.yaml`.

## Current Canonical Contract Summary

| Parameter            | Value                                    |
| -------------------- | ---------------------------------------- |
| Pipeline ID          | `composite_molecule`                     |
| Provider             | `composite`                              |
| Entity               | `molecule`                               |
| Seed Pipeline        | `chembl_molecule`                        |
| Enrichers            | `pubchem_compound`                       |
| Join Keys            | `inchi_key`, fallback `canonical_smiles` |
| Conflict Resolution  | `seed_priority`                          |
| Preserve All Sources | `true`                                   |
| Silver Output        | `data/output/silver/composite/molecule`  |
| Gold Output          | `data/output/gold/composite/molecule`    |

## Notes

- Current contract uses snake_case field names such as `molecule_id`,
  `inchi_key`, `canonical_smiles`, `pref_name`, `molecular_weight`,
  `standard_inchi`.
- Canonical field aliasing between ChEMBL and PubChem is maintained in the
  composite YAML config; this page no longer republishes the older dashed join
  notes.
- Composite join/control fields inherit canonical source-profile normalization.
  `inchi_key` and `canonical_smiles` are covered by composite join-key policy,
  while `molecule_id` and propagated controlled fields such as `molecule_type`
  must remain governed by the `chembl_molecule` profile before merge.
- For merge priorities, field aliases, and output groups, use the composite
  YAML config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Canonical guide      | [pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)                |
| Gold contract export | [composite_molecule_v1.0.json](../../contracts/gold/composite_molecule_v1.0.json)        |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [composite_molecule_v1.0.json](../../contracts/gold/composite_molecule_v1.0.json)        |
| Published-page role           | Pass   | Historical deep spec or summary is explicitly bounded by current canonical sources       |
