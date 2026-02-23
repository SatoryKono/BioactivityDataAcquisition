# Composite Activity Pipeline

*Updated: 2026-02-17*

## Overview

Combines ChEMBL bioactivity data with compound record metadata, enabling correlation of activity measurements with original compound names and document references.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite_activity` |
| Provider | `composite` |
| Entity | `activity` |
| Version | `1.0.0` |
| Config | `configs/pipelines/composite/activity.yaml` |

## Seed and Dependencies

- **Seed**: `chembl_activity`
- **Dependencies**: `chembl_compound_record` (filtered by `molecule-id` + `publication-id` dual-key)
- **Enrichers**: none

## Join Strategy

- Composite key: (`molecule-id`, `publication-id`)
- Activity to CompoundRecord is ~1:1 with composite key (one compound record per molecule-document pair)
- Merge uses `left-outer` to preserve all activities

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/activity` |
| Gold | `data/output/gold/composite/activity` |

## Merge Features

- **Conflict Resolution**: `seed-priority` — activity values always win
- **Preserve All Sources**: `false` — coalesce to unified fields
- **Field Priorities**: `molecule-id` and `publication-id` from seed are authoritative
- **Dependency Thresholds**: compound-record soft-fail 30%, hard-fail 70% (many activities lack compound records)

## Column Groups

| Group | Fields |
|-------|--------|
| system | entity-id, content-hash, -run-id, -run-type, -source-batch-id, ... |
| identifiers | activity-id, molecule-id, assay-id, target-id, publication-id |
| activity-values | standard-type, standard-relation, standard-value, standard-units, pchembl-value, ... |
| original-values | type, relation, value, units, text-value, ... |
| ligand-efficiency | ligand-efficiency-bei, le, lle, sei |
| compound-record | record-id, compound-key, compound-name, src-compound-id |
| molecule-context | canonical-smiles, molecule-pref-name, parent-molecule-id |
| target-context | target-pref-name, target-organism, taxonomy-id |
| assay-context | assay-type, assay-description, bao-format, bao-label, bao-endpoint, ... |
| document-context | document-journal, document-year |
| quality | data-validity-comment, potential-duplicate, manual-curation-flag, ... |

## Execution

- Max concurrency: 2
- Checkpoint enabled: true
- Retry: 3 attempts, 2x backoff

## Related Configs

- DQ rules: `configs/quality/entities/composite/activity.yaml`
- Filters: `configs/filters/entities/composite/activity.yaml`
- Schema: `configs/schemas/composite/activity.yaml`

## Related ADRs

- [ADR-026](../../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) (Composite Pipeline Pattern)
- [ADR-028](../../../02-architecture/decisions/ADR-028-filter-rules-externalization.md) (Filter Rules Externalization)
- [ADR-029](../../../02-architecture/decisions/ADR-029-output-metadata-unification.md) (Output Metadata Unification)
