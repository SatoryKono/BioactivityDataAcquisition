# ChEMBL Publication Similarity Pipeline

*Updated: 2026-02-03*

## Overview

Extracts publication similarity data (Tanimoto coefficients) from the ChEMBL `/document_similarity` endpoint.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `chembl_publication_similarity` |
| Provider | `chembl` |
| Entity | `publication_similarity` |
| Version | `2.1.0` |
| Loading Strategy | `full_scan_only` (force full scan) |
| Primary Keys | `sim_id` |
| Config | `configs/pipelines/chembl/publication_similarity.yaml` |

## Outputs

| Layer | Path |
|-------|------|
| Bronze | `data/output/bronze/chembl/publication_similarity` |
| Silver | `data/output/silver/chembl/publication_similarity` |
| Gold | `data/output/gold/chembl/publication_similarity` |

## Related Configs

- DQ: `configs/dq/entities/chembl/publication_similarity.yaml`
- Filters: `configs/filter/entities/chembl/publication_similarity.yaml`
- Column groups: `configs/data_schema/chembl/publication_similarity.yaml`

## Related ADRs

- [ADR-024](../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [ADR-030](../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)
- [ADR-031](../../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)
