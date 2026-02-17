# ChEMBL Publication Term Pipeline

*Updated: 2026-02-03*

## Overview

Derived pipeline that extracts and flattens publication terms (MeSH, keywords) from ChEMBL publication records.

## Identity

| Field            | Value                                                   |
| ---------------- | ------------------------------------------------------- |
| Pipeline ID      | `chembl_publication_term`                               |
| Provider         | `chembl`                                                |
| Entity           | `publication_term` (derived from `/document`)           |
| Version          | `2.1.0`                                                 |
| Loading Strategy | `full_scan_only` (force full scan)                      |
| Primary Keys     | `entity_id` (hash of publication_id + term_type + term) |
| Config           | `configs/pipelines/chembl/publication_term.yaml`        |

## Outputs

| Layer  | Path                                         |
| ------ | -------------------------------------------- |
| Bronze | `data/output/bronze/chembl/publication_term` |
| Silver | `data/output/silver/chembl/publication_term` |
| Gold   | `data/output/gold/chembl/publication_term`   |

## Related Configs

- DQ: `configs/quality/entities/chembl/publication_term.yaml`
- Filters: `configs/filters/entities/chembl/publication_term.yaml`
- Column groups: `configs/schemas/chembl/publication_term.yaml`

## Related ADRs

- [ADR-024](../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [ADR-030](../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)
- [ADR-031](../../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)
