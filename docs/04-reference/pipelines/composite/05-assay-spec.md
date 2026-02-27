# Composite Assay Pipeline

*Updated: 2026-02-17*

## Overview

Enriches ChEMBL assay data with cell line and tissue metadata from pre-populated Silver tables, providing full experimental context for downstream analysis.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite-assay` |
| Provider | `composite` |
| Entity | `assay` |
| Version | `1.0.0` |
| Config | `configs/composites/assay.yaml` |

## Seed and Enrichers

- **Seed**: `chembl-assay`
- **Dependencies**: none
- **Enrichers**: `chembl-cell-line` (cell context), `chembl-tissue` (tissue context)

## Architecture Note

Uses **enrichers** (not dependencies) because cell-line and tissue are reference tables already populated in Silver — no additional API calls needed, just lookup from existing Silver tables. Enrichers execute in parallel.

## Join Strategy

- `cell-id` and `tissue-id` are nullable FKs from seed
- ~70% of assays lack cell-line or tissue data
- Merge uses `left-outer` to preserve all assays
- Filter conditions: `cell-id IS NOT NULL` / `tissue-id IS NOT NULL`

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/assay` |
| Gold | `data/output/gold/composite/assay` |

## Merge Features

- **Conflict Resolution**: `seed-priority` — assay values always win
- **Preserve All Sources**: `false` — coalesce to unified fields
- **Field Mappings** (conflict resolution):
  - `chembl.cell-line.efo-id` -> `cell-efo-id`
  - `chembl.tissue.efo-id` -> `tissue-efo-id`
  - `chembl.tissue.pref-name` -> `tissue-pref-name`
  - `chembl.tissue.uberon-id` -> `tissue-uberon-id`
  - `chembl.tissue.bto-id` -> `tissue-bto-id`
  - `chembl.tissue.caloha-id` -> `tissue-caloha-id`
- **Exclude Fields**: cell-line PK (`cell-id` from enricher), tissue PK (`tissue-id` from enricher) — seed FKs retained
- **Enricher Thresholds**: soft-fail 70%, hard-fail 95% (most assays lack cell/tissue data)

## Column Groups

| Group | Fields |
|-------|--------|
| system | entity-id, content-hash, -run-id, -run-type, -source-batch-id, ... |
| identifiers | assay-id, cell-id, tissue-id, target-id, publication-id, src-id, src-assay-id, aidx |
| classification | assay-type, assay-category, assay-test-type, confidence-score, ... |
| biological-context | assay-organism, assay-taxonomy-id, assay-strain, assay-tissue, ... |
| description | description, score |
| ontology | bao-format, bao-label |
| cell-line | cell-name, cell-description, cell-type, cell-source-organism, cellosaurus-id, ... |
| tissue | tissue-pref-name, tissue-uberon-id, tissue-bto-id, tissue-caloha-id, tissue-efo-id |
| variant | variant-accession, variant-mutation, variant-sequence, ... |
| complex | assay-classifications, assay-parameters |

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
