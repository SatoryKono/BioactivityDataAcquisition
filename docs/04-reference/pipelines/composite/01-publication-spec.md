# Composite Publication Pipeline

*Updated: 2026-02-17*

## Overview

Merges publication data from multiple providers into a decomposed composite model with:

- canonical provider-agnostic core table;
- provider extension tables;
- lineage metadata table;
- temporary compatibility view preserving legacy denormalized interface.

## Identity

| Field       | Value                                          |
| ----------- | ---------------------------------------------- |
| Pipeline ID | `composite_publication`                        |
| Provider    | `composite`                                    |
| Entity      | `publication`                                  |
| Version     | `1.3.0`                                        |
| Config      | `configs/pipelines/composite/publication.yaml` |

## Seed and Enrichers

- **Seed**: `chembl_publication`
- **Enrichers**: `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication`
- **Dependencies**: none

## Logical Output Tables

| Surface                                     | Role                                             | Key                                                |
| ------------------------------------------- | ------------------------------------------------ | -------------------------------------------------- |
| `composite_publication_core`                | Canonical publication fields (provider-agnostic) | `publication_id`                                   |
| `composite_publication_ext_crossref`        | CrossRef-qualified extension fields              | `publication_id` (+ provider-native IDs if needed) |
| `composite_publication_ext_openalex`        | OpenAlex-qualified extension fields              | `publication_id`                                   |
| `composite_publication_ext_pubmed`          | PubMed-qualified extension fields                | `publication_id`                                   |
| `composite_publication_ext_semanticscholar` | Semantic Scholar-qualified extension fields      | `publication_id`                                   |
| `composite_publication_lineage`             | Merge/run lineage metadata                       | `publication_id`, `_composite_run_id`              |
| `composite_publication_compat_vw`           | Backward-compatible legacy interface (view)      | `publication_id`                                   |

## Physical Outputs

| Layer  | Path                                       |
| ------ | ------------------------------------------ |
| Silver | `data/output/silver/composite/publication` |
| Gold   | `data/output/gold/composite/publication`   |

> Note: physical path remains unchanged; decomposition defines logical contracts inside the composite publication dataset.

## Merge Features

- **Conflict Resolution**: `seed_priority` — seed (ChEMBL) values always win over enricher values for canonical core fields.
- **Provider Isolation**: enricher-only fields are stored in provider extension tables (no longer mixed into core contract).
- **Lineage Isolation**: `_composite_*`, `_source_providers`, `_enrichment_status`, `_lineage_*` moved to lineage table.
- **Compatibility Mode**: `composite_publication_compat_vw` reconstructs previous denormalized interface for migration period.

## Compatibility View Contract

During migration, downstream consumers that still expect the historical composite publication interface SHOULD read:

- `composite_publication_compat_vw`

The view is defined as:

```sql
SELECT
    c.*,
    xcr.*,
    xoa.*,
    xpm.*,
    xss.*,
    l.*
FROM composite_publication_core AS c
LEFT JOIN composite_publication_ext_crossref AS xcr USING (publication_id)
LEFT JOIN composite_publication_ext_openalex AS xoa USING (publication_id)
LEFT JOIN composite_publication_ext_pubmed AS xpm USING (publication_id)
LEFT JOIN composite_publication_ext_semanticscholar AS xss USING (publication_id)
LEFT JOIN composite_publication_lineage AS l
  ON l.publication_id = c.publication_id;
```

## Related Configs

- Field map: `configs/schemas/composite/publication.yaml`
- Filters: `configs/filters/entities/composite/publication.yaml`

## Related ADRs

- [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-029](../../02-architecture/decisions/ADR-029-output-metadata-unification.md)
- [ADR-035](../../02-architecture/decisions/ADR-035-composite-decomposition-strategy.md)
