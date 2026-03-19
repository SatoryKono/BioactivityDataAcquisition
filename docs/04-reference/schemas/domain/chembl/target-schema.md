# Target Schema (ChEMBL)

> **Status**: Historical deep schema note. Current canonical contract lives in
> [../../../providers/chembl/target.md](../../../providers/chembl/target.md)
> and
> [../../../../../configs/entities/chembl/target.yaml](../../../../../configs/entities/chembl/target.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `chembl_target` |
| Provider | `chembl` |
| Entity | `target` |
| Business Primary Keys | `["target_id"]` |
| Silver Partition Key | `target_type` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `target_id`,
  `target_type`, `pref_name`, `taxonomy_id`, `species_group_flag`,
  `target_components`, `component_ids`, `component_accessions`,
  `component_relationships`.
- This page no longer republishes the older dashed field tables such as
  `target-type`, `pref-name`, `component-id`, or `target-components`.
- For Gold filters, field groups, aliases, and DQ rules, use the target entity
  config above.
