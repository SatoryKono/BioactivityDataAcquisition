# Data Flow

*Aligned with RULES.md v5.24 (Local-Only Deployment)*

## Overview

Medallion Architecture — трёхслойная модель хранения данных: Bronze → Silver → Gold.

----------------------------------------------------------------------

## Medallion Architecture Diagram

> **Diagram:** See [`03-medallion-data-flow.mmd`](../architecture/03-medallion-data-flow.mmd)
> *(rendered не публикуются; используй source `.mmd`)*

----------------------------------------------------------------------

## Layer Specifications (§2.1)

| Layer      | Format          | Validation       | Retention         | Idempotency            |
| ---------- | --------------- | ---------------- | ----------------- | ---------------------- |
| **Bronze** | JSONL + zstd    | None             | 90 days → Archive | Append-only            |
| **Silver** | Delta Lake      | Pandera (soft)   | Permanent         | Merge/Upsert           |
| **Gold**   | Delta Lake      | Pandera (strict) | Permanent         | SCD Type 2 / Overwrite |

----------------------------------------------------------------------

## Storage Paths

> **Note**: Active runtime использует только локальную файловую систему.
> Эта страница документирует поддерживаемый Local-Only путь, без distributed-storage вариантов.

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
│           └── _delta_log/
│
├── gold/
│   └── {provider}/{entity}/
│       └── _delta_log/
│
├── quarantine/
│   └── common.quarantine/
│       └── _delta_log/
│
└── checkpoints/
    └── {pipeline-name}.json
```

**Note**: Silver partitioning is **configurable** via `partition-by` field in pipeline YAML configs.
Examples: `["year", "month"]`, `["assay-type"]`, `["organism"]`, or `[]` (no partitioning).
See `configs/entities/{provider}/{entity}.yaml` for specific configurations.

----------------------------------------------------------------------

## Pipeline Execution Flow

> **Diagram:** See [`04-pipeline-execution-flow.mmd`](../architecture/04-pipeline-execution-flow.mmd)
> *(rendered не публикуются; используй source `.mmd`)*

----------------------------------------------------------------------

## Required Metadata Fields (§2.4)

| Field              | Type      | Description                            |
| ------------------ | --------- | -------------------------------------- |
| `_run_id`          | UUID      | Pipeline execution ID                  |
| `_run_type`        | Enum      | `incremental` / `backfill` / `rebuild` |
| `_source_batch_id` | UUID      | Lineage reference in metadata sidecar  |
| `_ingestion_ts`    | Timestamp | UTC ingestion time                     |
| `content_hash`     | String    | SHA256 for deduplication               |
| `_dq_warn`         | Boolean   | Data quality warning flag              |

----------------------------------------------------------------------

## Silver → Gold Transformation

При записи в Gold слой выполняется трансформация:

1. **Фильтрация записей**: `should_write_gold()` определяет, какие записи попадают в Gold
1. **Исключение JSON полей**: `transform_for_gold()` удаляет поля из `GOLD_EXCLUDE_FIELDS`:
   - `molecule-hierarchy`, `molecule-properties`, `molecule-structures`
   - `molecule-synonyms`, `cross-references`, `atc-classifications`
1. **Валидация**: Pandera схема (strict mode) проверяет плоские поля

**Code Reference**: `src/bioetl/application/core/base_transformer.py` → `BaseTransformer.transform_for_gold()`

----------------------------------------------------------------------

## Data Quality Flow (§2.6)

```mermaid
flowchart TD
  INPUT["Input Record"] --> VALIDATE["Pandera Validate"]
  VALIDATE -->|Pass| SILVER["Silver Table"]
  VALIDATE -->|Warning < 5%| SILVER-WARN["Silver + _dq_warn=true"]
  VALIDATE -->|Error > 20%| FAIL["Batch FAIL"]
  VALIDATE -->|Per - record error| QUARANTINE["Quarantine Table"]
  QUARANTINE --> REPLAY["Manual Replay<br/>(after fix)"]
```

**Thresholds**:

- `< 5%` errors → Write with `_dq_warn=true`
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

- **System Context**: [system-context.md](../../system-context.md)
- **Architecture Diagrams**: [policy.md](../governance/policy.md)
