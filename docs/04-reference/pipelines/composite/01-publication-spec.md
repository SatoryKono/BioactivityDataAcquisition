# Composite Publication Pipeline

*Updated: 2026-02-03*

## Overview

Merges publication data from multiple providers into a unified composite publication table.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `composite_publication` |
| Provider | `composite` |
| Entity | `publication` |
| Version | `1.2.0` |
| Config | `configs/pipelines/composite/publication.yaml` |

## Seed and Enrichers

- **Seed**: `chembl_publication`
- **Enrichers**: `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`
- **Dependencies**: none

## Outputs

| Layer | Path |
|-------|------|
| Silver | `data/output/silver/composite/publication` |
| Gold | `data/output/gold/composite/publication` |

## Related Configs

- Field map: `configs/schemas/composite/publication.yaml`
- Filters: `configs/filters/entities/composite/publication.yaml`

## Related ADRs

- [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-028](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-029](../../02-architecture/decisions/ADR-029-output-metadata-unification.md)
