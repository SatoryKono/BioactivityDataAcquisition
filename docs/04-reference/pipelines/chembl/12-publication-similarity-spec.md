# ChEMBL Publication Similarity Pipeline

*Updated: 2026-02-03*

## Overview

Extracts publication similarity data (Tanimoto coefficients) from the ChEMBL `/document-similarity` endpoint.

## Identity

| Field | Value |
|-------|-------|
| Pipeline ID | `chembl-publication-similarity` |
| Provider | `chembl` |
| Entity | `publication-similarity` |
| Version | `2.1.0` |
| Loading Strategy | `full-scan-only` (force full scan) |
| Primary Keys | `sim-id` |
| Config | `configs/pipelines/chembl/publication-similarity.yaml` |

## Outputs

| Layer | Path |
|-------|------|
| Bronze | `data/output/bronze/chembl/publication-similarity` |
| Silver | `data/output/silver/chembl/publication-similarity` |
| Gold | `data/output/gold/chembl/publication-similarity` |

## Related Configs

- DQ: `configs/quality/entities/chembl/publication-similarity.yaml`
- Filters: `configs/filters/entities/chembl/publication-similarity.yaml`
- Column groups: `configs/schemas/chembl/publication-similarity.yaml`

## Related ADRs

- [ADR-024](../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [ADR-030](../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)
- [ADR-031](../../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)
