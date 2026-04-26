______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-24'

______________________________________________________________________

**⚠️ HISTORICAL CONTENT - ARCHIVED**

This page has been moved to the archive section and is no longer part of the active reference surface.

# Target Schema (ChEMBL) - Historical

**Current Schema**: [ChEMBL target provider reference](../../../providers/chembl/target.md)

**Current Config**: `configs/entities/chembl/target.yaml`

> **Status**: Historical deep schema note. Current canonical contract lives in
> [../../../providers/chembl/target.md](../../../providers/chembl/target.md)
> and
> `configs/entities/chembl/target.yaml`.

## Migration Notes

- **Status**: This schema page was moved to archive on 2026-04-24 as part of Issue #3092
- **Reason**: Historical deep schema pages create ambiguity with current canonical contracts
- **Replacement**: Use provider reference and entity config for current schema expectations

## Current Canonical Contract Summary

| Parameter             | Value           |
| --------------------- | --------------- |
| Pipeline ID           | `chembl_target` |
| Provider              | `chembl`        |
| Entity                | `target`        |
| Business Primary Keys | `["target_id"]` |
| Silver Partition Key  | `target_type`   |
| Silver Format         | `delta`         |
| Gold Format           | `delta`         |
| Gold Mode             | `scd2`          |

## Notes

- Current canonical field names are snake_case, for example `target_id`,
  `target_type`, `pref_name`, `taxonomy_id`, `species_group_flag`,
  `target_components`, `component_ids`, `component_accessions`,
  `component_relationships`.
- This page no longer republishes the older dashed field tables such as
  `target-type`, `pref-name`, `component-id`, or `target-components`.
- For Gold filters, field groups, aliases, and DQ rules, use the target entity
  config above.
