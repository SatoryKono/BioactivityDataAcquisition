# Data Flow

*Aligned with RULES.md v5.20 (Local-Only Deployment)*

## Overview

Medallion Architecture — трёхслойная модель хранения данных: Bronze → Silver → Gold.

----------------------------------------------------------------------

## Medallion Architecture Diagram

```mermaid
flowchart LR
  subgraph Sources["External Sources"]
    SRC1["ChEMBL"]
    SRC2["PubChem"]
    SRC3["UniProt"]
  end

  subgraph Bronze["Bronze Layer"]
    direction TB
    B1["JSONL + zstd"]
    B2["Append-only"]
    B3["90 days retention"]
  end

  subgraph Silver["Silver Layer"]
    direction TB
    S1["Delta Lake"]
    S2["Merge/Upsert"]
    S-perm["Permanent"]
  end

  subgraph Gold["Gold Layer"]
    direction TB
    G1["Delta / Parquet"]
    G2["SCD Type 2"]
    G3["Permanent"]
  end

  subgraph Side["Side Tables"]
    Q["Quarantine<br/>(DQ failures)"]
    L["Lineage Log<br/>(Provenance)"]
  end

  Sources -->|REST API| Bronze
  Bronze -->|Transform + Validate| Silver
  Silver -->|Transform + Filter| Gold
  Silver -.->|DQ errors| Q
  Bronze -.->|batch-id FK| L
```

----------------------------------------------------------------------

## Layer Specifications (§2.1)

| Layer      | Format          | Validation       | Retention         | Idempotency            |
| ---------- | --------------- | ---------------- | ----------------- | ---------------------- |
| **Bronze** | JSONL + zstd    | None             | 90 days → Archive | Append-only            |
| **Silver** | Delta Lake      | Pandera (soft)   | Permanent         | Merge/Upsert           |
| **Gold**   | Delta / Parquet | Pandera (strict) | Permanent         | SCD Type 2 / Overwrite |

----------------------------------------------------------------------

## Storage Paths

> **Note**: Local-Only deployment использует локальную файловую систему.
> Для распределённого развёртывания (future) — S3/MinIO.

```
data/output/                       # Local-Only (current)
├── bronze/
│   └── {provider}/{entity}/{date}/
│       ├── batch-001.jsonl.zst
│       └── -manifest.json
│
├── silver/
│   └── {provider}/{entity}/
│       └── [{partition-cols}/]  # Optional, configured via `partition-by` in YAML
│           └── -delta-log/
│
├── gold/
│   └── {provider}/{entity}/
│       └── -delta-log/
│
├── quarantine/
│   └── {provider}/{entity}/
│       └── {date}/
│
└── checkpoints/
    └── {pipeline-name}.json
```

**Note**: Silver partitioning is **configurable** via `partition-by` field in pipeline YAML configs.
Examples: `["year", "month"]`, `["assay-type"]`, `["organism"]`, or `[]` (no partitioning).
See `configs/pipelines/{provider}/{entity}.yaml` for specific configurations.

----------------------------------------------------------------------

## Pipeline Execution Flow

```mermaid
flowchart TB
  subgraph Prepare
    A1["Lock Acquire<br/>(MemoryLock)"]
    A2["Load Config"]
    A3["Checkpoint Load<br/>(if --resume)"]
  end

  subgraph Extract
    B1["Fetch from API<br/>(Circuit Breaker)"]
    B2["Write Bronze<br/>(JSONL + zstd)"]
    B3["Record Lineage"]
  end

  subgraph Transform
    C1["Normalize Values"]
    C2["Add Metadata<br/>(-run-id, -run-type)"]
    C3["Compute Content Hash"]
  end

  subgraph Validate
    D1["Pandera Schema"]
    D2["DQ Metrics"]
    D3["Route to Quarantine"]
  end

  subgraph Load
    E1["Safety Guard<br/>(validate lock)"]
    E2["Delta Lake Write<br/>(Silver)"]
    E3["Gold Transform<br/>(exclude JSON fields)"]
    E4["Delta Lake Write<br/>(Gold)<br/><i>skipped if skip-gold=True</i>"]
  end

  subgraph Finalize
    F1["Delete Checkpoint"]
    F2["Release Lock"]
    F3["Publish Metrics"]
  end

  A1 --> A2 --> A3 --> B1
  B1 --> B2 --> B3 --> C1
  C1 --> C2 --> C3 --> D1
  D1 --> D2 --> D3 --> E1
  E1 --> E2 --> E3 --> E4 --> F1
  F1 --> F2 --> F3
```

----------------------------------------------------------------------

## Required Metadata Fields (§2.4)

| Field              | Type      | Description                            |
| ------------------ | --------- | -------------------------------------- |
| `-run-id`          | UUID      | Pipeline execution ID                  |
| `-run-type`        | Enum      | `incremental` / `backfill` / `rebuild` |
| `-source-batch-id` | UUID      | FK to lineage-log                      |
| `-ingestion-ts`    | Timestamp | UTC ingestion time                     |
| `-content-hash`    | String    | SHA256 for deduplication               |
| `-dq-warn`         | Boolean   | Data quality warning flag              |

----------------------------------------------------------------------

## Silver → Gold Transformation

При записи в Gold слой выполняется трансформация:

1. **Фильтрация записей**: `should-write-gold()` определяет, какие записи попадают в Gold
1. **Исключение JSON полей**: `transform-for-gold()` удаляет поля из `GOLD-EXCLUDE-FIELDS`:
   - `molecule-hierarchy`, `molecule-properties`, `molecule-structures`
   - `molecule-synonyms`, `cross-references`, `atc-classifications`
1. **Валидация**: Pandera схема (strict mode) проверяет плоские поля

**Code Reference**: `src/bioetl/application/core/base-transformer.py` → `BaseTransformer.transform-for-gold()`

----------------------------------------------------------------------

## Data Quality Flow (§2.6)

```mermaid
flowchart TD
  INPUT["Input Record"] --> VALIDATE["Pandera Validate"]
  VALIDATE -->|Pass| SILVER["Silver Table"]
  VALIDATE -->|Warning < 5%| SILVER-WARN["Silver + -dq-warn=true"]
  VALIDATE -->|Error > 20%| FAIL["Batch FAIL"]
  VALIDATE -->|Per - record error| QUARANTINE["Quarantine Table"]
  QUARANTINE --> REPLAY["Manual Replay<br/>(after fix)"]
```

**Thresholds**:

- `< 5%` errors → Write with `-dq-warn=true`
- `5-20%` errors → Warning in logs
- `> 20%` errors → Batch fails entirely

----------------------------------------------------------------------

## Error Handling Summary

| Error Type                          | Action                         | Reference |
| ----------------------------------- | ------------------------------ | --------- |
| **Transient** (timeout, rate limit) | Retry with exponential backoff | §3.1.3    |
| **Circuit Breaker** (5 consecutive) | Open for 5 min, then half-open | §3.1.4    |
| **Data Quality**                    | Route to Quarantine            | §2.6      |
| **Lock Lost**                       | Abort to prevent split-brain   | §3.3      |

----------------------------------------------------------------------

## Related Documents

- **System Context**: [system-context.md](system-context.md)
- **Architecture Diagrams**: [diagrams/00-diagramming-policy.md](diagrams/00-diagramming-policy.md)
