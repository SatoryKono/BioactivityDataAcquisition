# Pipeline: ChEMBL Activity

> **Full Documentation (RU):** [docs/providers/chembl/activity.md](../../providers/chembl/activity.md)

## Overview

| Property | Value |
|----------|-------|
| **Pipeline Name** | `chembl_activity` |
| **Provider** | ChEMBL |
| **Entity** | Activity |
| **Configuration** | `configs/pipelines/chembl/activity.yaml` |
| **Primary Key** | `activity_id` |
| **Schema Version** | 1.0.0 |

## Description

This pipeline extracts bioactivity data from the ChEMBL database. Each record represents a measurement of biological activity (IC50, Ki, etc.) for a molecule-target pair.

## Data Schema (Silver Layer)

The Activity entity contains **55 fields**. Key fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `activity_id` | `string` | **Yes** | Unique activity record ID |
| `molecule_chembl_id` | `string` | **Yes** | ChEMBL molecule ID (e.g., `CHEMBL25`) |
| `target_chembl_id` | `string` | No | ChEMBL target ID |
| `standard_type` | `string` | No | Measurement type: IC50, Ki, EC50, etc. |
| `standard_value` | `float` | No | Standardized measurement value |
| `standard_units` | `string` | No | Units: nM, uM, etc. |
| `pchembl_value` | `float` | No | -log10(IC50 in molar) |
| `canonical_smiles` | `string` | No | SMILES structure |
| `action_type_action_type` | `string` | No | Action type: INHIBITOR, AGONIST, etc. |
| `action_type_description` | `string` | No | Description of action type |
| `action_type_parent_type` | `string` | No | Parent grouping (nullable) |
| `entity_id` | `string` | Auto | `chembl:{activity_id}` |
| `content_hash` | `string` | Auto | SHA256 hash for versioning |

## Data Quality Rules

| Rule | Condition | Action |
|------|-----------|--------|
| Positive value | `standard_value > 0` | Quarantine if violated |
| Known type | `standard_type` in known enum | Warning if unknown |
| Valid molecule ID | `molecule_chembl_id` matches `^CHEMBL\d+$` | Quarantine if invalid |

### Error Thresholds

| Threshold | Condition | Action |
|-----------|-----------|--------|
| Soft | > 5% errors in batch | Log WARNING |
| Hard | > 20% errors in batch | Fail batch |

## Storage Layers

| Layer | Format | Mode | Path Pattern |
|-------|--------|------|--------------|
| Bronze | JSONL + Zstd | Append-only | `bronze/v1/chembl/activity/{date}/batch_{id}.jsonl.zst` |
| Silver | Delta Lake | Merge by `activity_id` | `silver/chembl_activity/` |
| Gold | Delta Lake | Overwrite | `gold/chembl_activity/` |

### Gold Filter Criteria

Records pass to Gold layer only if:
- `standard_value` is not null
- `standard_units` is present
- `target_chembl_id` is present
- `standard_type` is IC50 or Ki
- `data_validity_comment` is null (no data issues)

## CLI Usage

```bash
# Incremental load (default)
bioetl run chembl_activity

# With record limit
bioetl run chembl_activity --limit 1000

# Backfill
bioetl run chembl_activity --run-type backfill --start-date 2024-01-01

# Full rebuild
bioetl run chembl_activity --run-type rebuild
```

## Related Files

| Component | Path |
|-----------|------|
| Configuration | `configs/pipelines/chembl/activity.yaml` |
| Entity Definition | `src/bioetl/domain/entities.py` |
| Transformer | `src/bioetl/application/pipelines/chembl/activity_transformer.py` |
| Gold Filter | `src/bioetl/application/pipelines/chembl/activity_gold_filter.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |

---

*See [full documentation in Russian](../../providers/chembl/activity.md) for complete schema details, normalization rules, and data flow diagrams.*
