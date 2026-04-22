______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Composite Assay Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/assay.yaml`.

## Current Canonical Contract Summary

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| Pipeline ID          | `composite_assay`                    |
| Provider             | `composite`                          |
| Entity               | `assay`                              |
| Seed Pipeline        | `chembl_assay`                       |
| Enrichers            | `chembl_cell_line`, `chembl_tissue`  |
| Join Keys            | `cell_id`, `tissue_id`               |
| Merge Strategy       | `left_outer`                         |
| Conflict Resolution  | `seed_priority`                      |
| Preserve All Sources | `false`                              |
| Silver Output        | `data/output/silver/composite/assay` |
| Gold Output          | `data/output/gold/composite/assay`   |

## Notes

- Current contract uses snake_case field names such as `assay_id`, `cell_id`,
  `tissue_id`, `assay_type`, `confidence_score`, `tissue_pref_name`,
  `cell_efo_id`.
- Namespace disambiguation for overlapping enricher fields is defined in the
  YAML config via `field_mappings`; this page no longer republishes the older
  dashed rename tables.
- Composite join/control fields inherit canonical source-profile normalization.
  `cell_id` and `tissue_id` are covered by composite join-key policy, while
  propagated controlled fields such as `assay_type` and `bao_format` must remain
  governed by the `chembl_assay` profile before merge.
- For enricher thresholds, filter conditions, column groups, and merge rules,
  use the composite YAML config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Canonical guide      | [pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)                |
| Gold contract export | [composite_assay_v1.0.json](../../contracts/gold/composite_assay_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [composite_assay_v1.0.json](../../contracts/gold/composite_assay_v1.0.json)              |
| Published-page role           | Pass   | Historical deep spec or summary is explicitly bounded by current canonical sources       |
