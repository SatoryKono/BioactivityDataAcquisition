# ChEMBL Molecule Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/molecule.md](../../providers/chembl/molecule.md)
> and
> `configs/entities/chembl/molecule.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_molecule` |
| Provider | `chembl` |
| Entity | `molecule` |
| Business Primary Keys | `["molecule_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

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
