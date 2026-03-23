# Composite Activity Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/activity.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `composite_activity` |
| Provider | `composite` |
| Entity | `activity` |
| Seed Pipeline | `chembl_activity` |
| Dependencies | `chembl_compound_record` |
| Join Keys | `molecule_id`, `publication_id` |
| Merge Strategy | `left_outer` |
| Conflict Resolution | `seed_priority` |
| Preserve All Sources | `false` |
| Silver Output | `data/output/silver/composite/activity` |
| Gold Output | `data/output/gold/composite/activity` |

## Notes

- Current contract uses snake_case field names such as `activity_id`,
  `molecule_id`, `publication_id`, `standard_type`, `standard_value`,
  `document_journal`.
- The dependency uses multi-field filtering via `filter_fields` and joins on the
  composite key defined in the YAML config.
- This page no longer republishes the older dashed field tables, conflict notes,
  or threshold summaries.
- For merge settings, column groups, DQ rules, and output ordering, use the
  composite YAML config above.
