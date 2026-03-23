# ChEMBL Protein Classification Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/chembl/protein-class.md](../../providers/chembl/protein-class.md)
> and
> `configs/entities/chembl/protein_class.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_protein_class` |
| Provider | `chembl` |
| Entity | `protein_class` |
| Business Primary Keys | `["protein_class_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example
  `protein_class_id`, `parent_id`, `replaced_by`, `pref_name`, `short_name`,
  `protein_class_desc`, `definition`, `class_level`, `sort_order`,
  `downgraded`.
- This page no longer republishes older dashed labels such as
  `protein-class-id`, `parent-id`, `class-level`, or `sort-order` as the
  active contract.
- For hierarchy validation, filter settings, and partitioning details, use the
  provider reference and entity config above.
