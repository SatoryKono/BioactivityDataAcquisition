---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# PubChem Compound Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/pubchem/compound.md](../../providers/pubchem/compound.md)
> and
> `configs/entities/pubchem/compound.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `pubchem_compound` |
| Provider | `pubchem` |
| Entity | `compound` |
| Business Primary Keys | `["molecule_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

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
