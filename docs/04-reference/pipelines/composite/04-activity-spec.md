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
- **Dependencies**: `chembl_compound_record` (filtered by `molecule_id` + `publication_id` dual-key)
- **Enrichers**: none

## Join Strategy

- Composite key: (`molecule_id`, `publication_id`)
- Activity to CompoundRecord is ~1:1 with composite key (one compound record per molecule-document pair)
- Merge uses `left_outer` to preserve all activities

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/activity` |
| Gold | `data/output/gold/composite/activity` |

## Merge Features

- **Conflict Resolution**: `seed_priority` — activity values always win
- **Preserve All Sources**: `false` — coalesce to unified fields
- **Field Priorities**: `molecule_id` and `publication_id` from seed are authoritative
- **Dependency Thresholds**: compound_record soft_fail 30%, hard_fail 70% (many activities lack compound records)

## Column Groups

| Group | Fields |
|-------|--------|
| system | entity_id, content_hash, _run_id, _run_type, _source_batch_id, ... |
| identifiers | activity_id, molecule_id, assay_id, target_id, publication_id |
| activity_values | standard_type, standard_relation, standard_value, standard_units, pchembl_value, ... |
| original_values | type, relation, value, units, text_value, ... |
| ligand_efficiency | ligand_efficiency_bei, le, lle, sei |
| compound_record | record_id, compound_key, compound_name, src_compound_id |
| molecule_context | canonical_smiles, molecule_pref_name, parent_molecule_id |
| target_context | target_pref_name, target_organism, taxonomy_id |
| assay_context | assay_type, assay_description, bao_format, bao_label, bao_endpoint, ... |
| document_context | document_journal, document_year |
| quality | data_validity_comment, potential_duplicate, manual_curation_flag, ... |

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
