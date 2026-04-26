______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# PubChem Compound Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/pubchem/compound.md](../../providers/pubchem/compound.md)
> and
> `configs/entities/pubchem/compound.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value              |
| --------------------- | ------------------ |
| Pipeline ID           | `pubchem_compound` |
| Provider              | `pubchem`          |
| Entity                | `compound`         |
| Business Primary Keys | `["molecule_id"]`  |
| Silver Format         | `delta`            |
| Gold Format           | `delta`            |
| Gold Mode             | `scd2`             |

## Notes

- Current canonical field names are snake_case, for example `molecule_id`,
  `canonical_smiles`, `isomeric_smiles`, `inchi`, `inchi_key`,
  `molecular_formula`, `molecular_weight`, `exact_mass`, `monoisotopic_mass`,
  `xlogp`, `tpsa`, `heavy_atom_count`, `h_bond_donor_count`,
  `h_bond_acceptor_count`, `rotatable_bond_count`, `volume_3d`,
  `conformer_count_3d`.
- This page no longer republishes older mixed-case and dashed labels such as
  `CID`, `CanonicalSMILES`, `InChIKey`, `molecule-id`, `canonical-smiles`, or
  `volume-3d` as the active contract.
- For partitioning, DQ rules, and input-filter behavior, use the provider
  reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [compound.md](../../providers/pubchem/compound.md)                                       |
| Gold contract export | [pubchem_compound_v1.0.json](../../contracts/gold/pubchem_compound_v1.0.json)            |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [pubchem_compound_v1.0.json](../../contracts/gold/pubchem_compound_v1.0.json)            |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
