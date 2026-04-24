______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Composite Target Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/target.yaml`.

## Current Canonical Contract Summary

| Parameter            | Value                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------- |
| Pipeline ID          | `composite_target`                                                                        |
| Provider             | `composite`                                                                               |
| Entity               | `target`                                                                                  |
| Seed Pipeline        | `chembl_target`                                                                           |
| Dependencies         | `chembl_target_component`, `chembl_protein_class`, `uniprot_idmapping`, `uniprot_protein` |
| Join Flow            | seed `target_id` / `primary_component_id` plus chained dependency keys                    |
| Conflict Resolution  | `seed_priority`                                                                           |
| Preserve All Sources | `false`                                                                                   |
| Silver Output        | `data/output/silver/composite/target`                                                     |
| Gold Output          | `data/output/gold/composite/target`                                                       |

## Notes

- Current contract uses snake_case keys such as `target_id`,
  `primary_component_id`, `uniprot_accession`, `mapping_status`.
- Chained dependency behavior is defined in the composite YAML via `key_source`,
  `filter_field`, and `key_filter`; this page no longer republishes the older
  dashed dependency tables.
- Composite join/control fields inherit canonical source-profile normalization.
  `target_id`, `primary_component_id`, `protein_classification_id`, and
  `uniprot_accession` are covered by composite join-key policy; propagated
  controlled fields such as `target_type` must remain governed by the
  `chembl_target` profile before merge.
- For dependency order, merge priorities, and column groups, use the composite
  YAML config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Canonical guide      | [pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)                |
| Gold contract export | [composite_target_v1.0.json](../../contracts/gold/composite_target_v1.0.json)            |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [composite_target_v1.0.json](../../contracts/gold/composite_target_v1.0.json)            |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
