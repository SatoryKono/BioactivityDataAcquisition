# Composite Target Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../../03-guides/pipeline-configuration.md](../../../03-guides/pipeline-configuration.md)
> and
> `configs/composites/target.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `composite_target` |
| Provider | `composite` |
| Entity | `target` |
| Seed Pipeline | `chembl_target` |
| Dependencies | `chembl_target_component`, `chembl_protein_class`, `uniprot_idmapping`, `uniprot_protein` |
| Join Flow | seed `target_id` / `primary_component_id` plus chained dependency keys |
| Conflict Resolution | `seed_priority` |
| Preserve All Sources | `false` |
| Silver Output | `data/output/silver/composite/target` |
| Gold Output | `data/output/gold/composite/target` |

## Notes

- Current contract uses snake_case keys such as `target_id`,
  `primary_component_id`, `uniprot_accession`, `mapping_status`.
- Chained dependency behavior is defined in the composite YAML via `key_source`,
  `filter_field`, and `key_filter`; this page no longer republishes the older
  dashed dependency tables.
- For dependency order, merge priorities, and column groups, use the composite
  YAML config above.
