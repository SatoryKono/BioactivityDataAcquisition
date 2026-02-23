# Pipeline: ChEMBL Assay

> **Full Documentation (RU):** [docs/04-reference/providers/chembl/assay.md](../providers/chembl/assay.md)

## Overview

| Property           | Value                                 |
| ------------------ | ------------------------------------- |
| **Pipeline Name**  | `chembl_assay`                        |
| **Provider**       | ChEMBL                                |
| **Entity**         | Assay                                 |
| **Configuration**  | `configs/pipelines/chembl/assay.yaml` |
| **Primary Key**    | `assay-id`                            |
| **Config Version** | 1.2.0                                 |

## Description

This pipeline extracts bioassay definitions from the ChEMBL database. Each record describes an experimental assay, including its type (Binding, Functional), organism, and description.

## Data Schema (Silver Layer)

The Assay entity contains **43 fields**. Key fields include:

| Field                   | Type     | Required | Description                                      |
| ----------------------- | -------- | -------- | ------------------------------------------------ |
| `assay-id`              | `string` | **Yes**  | Unique assay ID (e.g., `CHEMBL1234`)             |
| `assay-type`            | `string` | **Yes**  | Type code: `B` (Binding), `F` (Functional), etc. |
| `description`           | `string` | No       | Text description of the assay                    |
| `assay-organism`        | `string` | No       | Organism name (e.g., `Homo sapiens`)             |
| `confidence-score`      | `int`    | No       | Quality score (0-9)                              |
| `assay-pref-name`       | `string` | No       | Preferred assay name (if available)              |
| `score`                 | `float`  | No       | Assay score (distinct from confidence-score)     |
| `publication-id`        | `string` | No       | Related publication ID                           |
| `variant-accession`     | `string` | No       | UniProt accession of variant                     |
| `variant-isoform`       | `string` | No       | Isoform identifier                               |
| `variant-mutation`      | `string` | No       | Mutation description (e.g., V600E)               |
| `variant-organism`      | `string` | No       | Variant organism name                            |
| `variant-sequence`      | `string` | No       | Amino acid sequence                              |
| `variant-tax-id`        | `int`    | No       | NCBI Taxonomy ID                                 |
| `variant-sequence-json` | `string` | No       | Original JSON (forensic)                         |
| `entity-id`             | `string` | Auto     | `chembl:{assay-id}`                              |
| `content-hash`          | `string` | Auto     | SHA256 hash for versioning                       |

## Data Quality Rules

| Rule       | Condition                                  | Action                |
| ---------- | ------------------------------------------ | --------------------- |
| Valid ID   | `assay-id` starts with `CHEMBL`            | Quarantine if invalid |
| Known Type | `assay-type` in known enum (B, F, A, T, U) | Warning               |

### Error Thresholds

| Threshold | Condition             | Action      |
| --------- | --------------------- | ----------- |
| Soft      | > 5% errors in batch  | Log WARNING |
| Hard      | > 20% errors in batch | Fail batch  |

## Storage Layers

| Layer  | Format     | Mode                | Path Pattern                       |
| ------ | ---------- | ------------------- | ---------------------------------- |
| Bronze | JSONL      | Append-only         | `data/output/bronze/chembl/assay/` |
| Silver | Delta Lake | Merge by `assay-id` | `data/output/silver/chembl/assay/` |
| Gold   | Delta Lake | Overwrite           | `data/output/gold/chembl/assay/`   |

**Note:** Silver layer is partitioned by `assay-type`.
**Note:** CSV export is enabled for Silver and Gold layers.

### Gold Filter Criteria

Records pass to Gold layer only if:

- `assay-type` is one of:
  - **B** (Binding)
  - **F** (Functional)
- `confidence-score` >= 4

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

| Component      | Path                                                           |
| -------------- | -------------------------------------------------------------- |
| Configuration  | `configs/pipelines/chembl/assay.yaml`                          |
| Pipeline Logic | `src/bioetl/application/pipelines/chembl/assay.py`             |
| Transformer    | `src/bioetl/application/pipelines/chembl/assay-transformer.py` |
| Gold Filter    | `configs/filters/entities/chembl/assay.yaml`                   |
| Data Quality   | `configs/quality/entities/chembl/assay.yaml`                   |
| Silver Schema  | `src/bioetl/infrastructure/schemas/silver.py`                  |
