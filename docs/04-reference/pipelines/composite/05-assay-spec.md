---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Composite Assay Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/assay.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `composite_assay` |
| Provider | `composite` |
| Entity | `assay` |
| Seed Pipeline | `chembl_assay` |
| Enrichers | `chembl_cell_line`, `chembl_tissue` |
| Join Keys | `cell_id`, `tissue_id` |
| Merge Strategy | `left_outer` |
| Conflict Resolution | `seed_priority` |
| Preserve All Sources | `false` |
| Silver Output | `data/output/silver/composite/assay` |
| Gold Output | `data/output/gold/composite/assay` |

## Notes

- Current contract uses snake_case field names such as `assay_id`, `cell_id`,
  `tissue_id`, `assay_type`, `confidence_score`, `tissue_pref_name`,
  `cell_efo_id`.
- Namespace disambiguation for overlapping enricher fields is defined in the
  YAML config via `field_mappings`; this page no longer republishes the older
  dashed rename tables.
- For enricher thresholds, filter conditions, column groups, and merge rules,
  use the composite YAML config above.
