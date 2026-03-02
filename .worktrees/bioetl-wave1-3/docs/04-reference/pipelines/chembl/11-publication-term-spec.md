# ChEMBL Publication Term Pipeline

*Updated: 2026-02-03*

## Overview

Derived pipeline that extracts and flattens publication terms (MeSH, keywords) from ChEMBL publication records.

## Identity

| Field            | Value                                                   |
| ---------------- | ------------------------------------------------------- |
| Pipeline ID      | `chembl_publication_term`                               |
| Provider         | `chembl`                                                |
| Entity           | `publication-term` (derived from `/document`)           |
| Version          | `2.1.0`                                                 |
| Loading Strategy | `full-scan-only` (force full scan)                      |
| Primary Keys     | `entity-id` (hash of publication-id + term-type + term) |
| Config           | `configs/entities/chembl/publication_term.yaml`        |

## Outputs

| Layer  | Path                                         |
| ------ | -------------------------------------------- |
| Bronze | `data/output/bronze/chembl/publication-term` |
| Silver | `data/output/silver/chembl/publication-term` |
| Gold   | `data/output/gold/chembl/publication-term`   |

## Related Configs

- DQ: `configs/entities/chembl/publication_term.yaml#quality`
- Filters: `configs/entities/chembl/publication_term.yaml#filters`
- Column groups: `configs/entities/chembl/publication_term.yaml#schema`

## Related ADRs

- [ADR-024](../../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [ADR-030](../../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)
- [ADR-031](../../../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)
