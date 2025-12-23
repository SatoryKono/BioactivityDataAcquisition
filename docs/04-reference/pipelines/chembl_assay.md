# Pipeline: ChEMBL Assay

> **Full Documentation (RU):** [docs/providers/chembl/assay.md](../../providers/chembl/assay.md)

## Overview

| Property | Value |
|----------|-------|
| **Pipeline Name** | `chembl_assay` |
| **Provider** | ChEMBL |
| **Entity** | Assay |
| **Configuration** | `configs/pipelines/chembl/assay.yaml` |
| **Primary Key** | `assay_chembl_id` |
| **Schema Version** | 1.0.0 |

## Description

This pipeline extracts bioassay definitions from the ChEMBL database. Each record describes an experimental assay, including its type (Binding, Functional), organism, and description.

## Data Schema (Silver Layer)

Key fields include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assay_chembl_id` | `string` | **Yes** | Unique assay ID (e.g., `CHEMBL1234`) |
| `assay_type` | `string` | **Yes** | Type code: `B` (Binding), `F` (Functional), etc. |
| `description` | `string` | No | Text description of the assay |
| `assay_organism` | `string` | No | Organism name (e.g., `Homo sapiens`) |
| `confidence_score` | `int` | No | Quality score (0-9) |
| `assay_pref_name` | `string` | No | Preferred assay name (if available) |
| `score` | `float` | No | Assay score (distinct from confidence_score) |
| `document_chembl_id` | `string` | No | Related publication ID |
| `entity_id` | `string` | Auto | `chembl:{assay_chembl_id}` |
| `content_hash` | `string` | Auto | SHA256 hash for versioning |

## Data Quality Rules

| Rule | Condition | Action |
|------|-----------|--------|
| Valid ID | `assay_chembl_id` starts with `CHEMBL` | Quarantine if invalid |
| Known Type | `assay_type` in known enum (B, F, A, T, U) | Warning |

### Error Thresholds

| Threshold | Condition | Action |
|-----------|-----------|--------|
| Soft | > 5% errors in batch | Log WARNING |
| Hard | > 20% errors in batch | Fail batch |

## Storage Layers

| Layer | Format | Mode | Path Pattern |
|-------|--------|------|--------------|
| Bronze | JSONL | Append-only | `data/output/bronze/chembl/assay/` |
| Silver | Delta Lake | Merge by `assay_chembl_id` | `data/output/silver/chembl_assay/` |
| Gold | Delta Lake | Overwrite | `data/output/gold/chembl_assay/` |

**Note:** Silver layer is partitioned by `assay_type`.
**Note:** CSV export is enabled for Silver and Gold layers.

### Gold Filter Criteria

Records pass to Gold layer only if:
- `assay_type` is one of:
    - **B** (Binding)
    - **F** (Functional)
- `confidence_score` >= 4

## CLI Usage

```bash
# Incremental load (default)
bioetl run --pipeline chembl_assay

# With record limit
bioetl run --pipeline chembl_assay --limit 100

# Full rebuild (re-fetch all data)
bioetl run --pipeline chembl_assay --run-type rebuild
```

## Related Files

| Component | Path |
|-----------|------|
| Configuration | `configs/pipelines/chembl/assay.yaml` |
| Pipeline Logic | `src/bioetl/application/pipelines/chembl/assay.py` |
| Transformer | `src/bioetl/application/pipelines/chembl/assay_transformer.py` |
| Gold Filter | `src/bioetl/application/pipelines/chembl/assay_filter.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold Schema | `src/bioetl/infrastructure/schemas/gold.py` |
