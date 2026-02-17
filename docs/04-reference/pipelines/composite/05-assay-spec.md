# Composite Assay Pipeline

*Updated: 2026-02-17*

## Overview

Enriches ChEMBL assay data with cell line and tissue metadata from pre-populated Silver tables, providing full experimental context for downstream analysis.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite_assay` |
| Provider | `composite` |
| Entity | `assay` |
| Version | `1.0.0` |
| Config | `configs/pipelines/composite/assay.yaml` |

## Seed and Enrichers

- **Seed**: `chembl_assay`
- **Dependencies**: none
- **Enrichers**: `chembl_cell_line` (cell context), `chembl_tissue` (tissue context)

## Architecture Note

Uses **enrichers** (not dependencies) because cell_line and tissue are reference tables already populated in Silver — no additional API calls needed, just lookup from existing Silver tables. Enrichers execute in parallel.

## Join Strategy

- `cell_id` and `tissue_id` are nullable FKs from seed
- ~70% of assays lack cell_line or tissue data
- Merge uses `left_outer` to preserve all assays
- Filter conditions: `cell_id IS NOT NULL` / `tissue_id IS NOT NULL`

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/assay` |
| Gold | `data/output/gold/composite/assay` |

## Merge Features

- **Conflict Resolution**: `seed_priority` — assay values always win
- **Preserve All Sources**: `false` — coalesce to unified fields
- **Field Mappings** (conflict resolution):
  - `chembl.cell_line.efo_id` -> `cell_efo_id`
  - `chembl.tissue.efo_id` -> `tissue_efo_id`
  - `chembl.tissue.pref_name` -> `tissue_pref_name`
  - `chembl.tissue.uberon_id` -> `tissue_uberon_id`
  - `chembl.tissue.bto_id` -> `tissue_bto_id`
  - `chembl.tissue.caloha_id` -> `tissue_caloha_id`
- **Exclude Fields**: cell_line PK (`cell_id` from enricher), tissue PK (`tissue_id` from enricher) — seed FKs retained
- **Enricher Thresholds**: soft_fail 70%, hard_fail 95% (most assays lack cell/tissue data)

## Column Groups

| Group | Fields |
|-------|--------|
| system | entity_id, content_hash, _run_id, _run_type, _source_batch_id, ... |
| identifiers | assay_id, cell_id, tissue_id, target_id, publication_id, src_id, src_assay_id, aidx |
| classification | assay_type, assay_category, assay_test_type, confidence_score, ... |
| biological_context | assay_organism, assay_taxonomy_id, assay_strain, assay_tissue, ... |
| description | description, score |
| ontology | bao_format, bao_label |
| cell_line | cell_name, cell_description, cell_type, cell_source_organism, cellosaurus_id, ... |
| tissue | tissue_pref_name, tissue_uberon_id, tissue_bto_id, tissue_caloha_id, tissue_efo_id |
| variant | variant_accession, variant_mutation, variant_sequence, ... |
| complex | assay_classifications, assay_parameters |

## Execution

- Max concurrency: 2 (both enrichers in parallel)
- Checkpoint enabled: true
- Retry: 3 attempts, 2x backoff

## Related Configs

- DQ rules: `configs/quality/entities/composite/assay.yaml`
- Filters: `configs/filters/entities/composite/assay.yaml`

## Related ADRs

- [ADR-026](../../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) (Composite Pipeline Pattern)
- [ADR-028](../../../02-architecture/decisions/ADR-028-filter-rules-externalization.md) (Filter Rules Externalization)
- [ADR-029](../../../02-architecture/decisions/ADR-029-output-metadata-unification.md) (Output Metadata Unification)
