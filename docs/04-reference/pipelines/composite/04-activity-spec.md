______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Composite Activity Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/activity.yaml`.

## Current Canonical Contract Summary

| Parameter            | Value                                   |
| -------------------- | --------------------------------------- |
| Pipeline ID          | `composite_activity`                    |
| Provider             | `composite`                             |
| Entity               | `activity`                              |
| Seed Pipeline        | `chembl_activity`                       |
| Dependencies         | `chembl_compound_record`                |
| Join Keys            | `molecule_id`, `publication_id`         |
| Merge Strategy       | `left_outer`                            |
| Conflict Resolution  | `seed_priority`                         |
| Preserve All Sources | `false`                                 |
| Silver Output        | `data/output/silver/composite/activity` |
| Gold Output          | `data/output/gold/composite/activity`   |

## Notes

- Current contract uses snake_case field names such as `activity_id`,
  `molecule_id`, `publication_id`, `standard_type`, `standard_value`,
  `document_journal`.
- The dependency uses multi-field filtering via `filter_fields` and joins on the
  composite key defined in the YAML config.
- Composite join/control fields inherit canonical source-profile normalization.
  `molecule_id` and `publication_id` are covered by composite join-key policy;
  propagated fields such as `standard_type`, `standard_relation`, `standard_flag`,
  `assay_type`, `bao_format`, and `bao_endpoint` must remain governed by
  `chembl_activity` profile rules before merge.
- This page no longer republishes the older dashed field tables, conflict notes,
  or threshold summaries.
- For merge settings, column groups, DQ rules, and output ordering, use the
  composite YAML config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Canonical guide      | [pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)                |
| Gold contract export | [composite_activity_v1.0.json](../../contracts/gold/composite_activity_v1.0.json)        |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [composite_activity_v1.0.json](../../contracts/gold/composite_activity_v1.0.json)        |
| Published-page role           | Pass   | Historical deep spec or summary is explicitly bounded by current canonical sources       |
