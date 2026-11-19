______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-19'

______________________________________________________________________

# ChEMBL Molecule Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/molecule.md](../../providers/chembl/molecule.md)
> and
> `configs/entities/chembl/molecule.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value             |
| --------------------- | ----------------- |
| Pipeline ID           | `chembl_molecule` |
| Provider              | `chembl`          |
| Entity                | `molecule`        |
| Business Primary Keys | `["molecule_id"]` |
| Silver Format         | `delta`           |
| Gold Format           | `delta`           |
| Gold Mode             | `scd2`            |

## Gold eligibility

Molecule Gold requires `molecule_id`, `molecule_type=Small molecule`,
`structure_type=MOL`, and `inorganic_flag=0`. These filters use fields available
in the Molecule Silver projection. `potential_duplicate` is absent from that
projection and is not an eligibility condition; it is not synthesized as zero.

Removing the unavailable condition restores business eligibility for matching
records and can expand the Gold cohort. Strict Gold validation, DQ dispositions,
primary keys, hash policy, extraction parameters and source-profile identity stay
unchanged. The effective-config digest changes with the corrected filter.
Previously excluded data requires reprocessing from preserved Bronze into a new
isolated output root; changing configuration alone does not repair stored outputs.

## Notes

- Current canonical field names are snake_case, for example `molecule_id`,
  `molecule_type`, `max_phase`, `canonical_smiles`, `standard_inchi`,
  `inchi_key`, `molecular_weight`, `logp`, `hierarchy_parent_chembl_id`,
  `hierarchy_active_chembl_id`, `hierarchy_child_chembl_id`.
- This page no longer republishes older dashed and nested API labels such as
  `molecule-id`, `molecule-type`, `canonical-smiles`, `standard-inchi-key`, or
  `molecule-hierarchy` as the active contract.
- For quality rules, aliases, and flattened field groups, use the provider
  reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [molecule.md](../../providers/chembl/molecule.md)                                        |
| Gold contract export | [chembl_molecule_v1.0.json](../../contracts/gold/chembl_molecule_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_molecule_v1.0.json](../../contracts/gold/chembl_molecule_v1.0.json)              |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
