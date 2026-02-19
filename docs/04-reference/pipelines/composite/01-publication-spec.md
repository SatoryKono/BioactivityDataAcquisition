# Composite Publication Pipeline

*Updated: 2026-02-15*

## Overview

Merges publication data from multiple providers into a unified composite publication table.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite-publication` |
| Provider | `composite` |
| Entity | `publication` |
| Version | `1.2.0` |
| Config | `configs/pipelines/composite/publication.yaml` |

## Seed and Enrichers

- **Seed**: `chembl-publication`
- **Enrichers**: `crossref-publication`, `openalex-publication`, `pubmed-publication`, `semanticscholar-publication`
- **Dependencies**: none

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/publication` |
| Gold | `data/output/gold/composite/publication` |

## Merge Features

- **Conflict Resolution**: `seed-priority` — seed (ChEMBL) values always win over enricher values
- **Preserve All Sources**: `true` — keeps provider-qualified columns (e.g., `crossref.publication.title`)
- **Cross-Validation**: Compares paired fields (doi, title, volume, issue, page-first, page-last, publication-year, citations-received) between seed and each enricher before merge. Mismatches trigger warnings, errors, or quarantine.
- **Exclude Fields**: 40 redundant enricher columns excluded from output (CV-validated fields that duplicate seed values, plus low-value fields)

## Related Configs

- Field map: `configs/schemas/composite/publication.yaml`
- Filters: `configs/filters/entities/composite/publication.yaml`

## Related ADRs

- [ADR-026](../../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-028](../../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-029](../../../02-architecture/decisions/ADR-029-output-metadata-unification.md)
