# Local Storage Layout

*Reference: [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

This guide describes the local filesystem layout used by BioETL in Local-Only mode.

## Directory Structure

```
data/
├── bronze/
│   └── v1/                          # Format version (JSONL + zstd)
│       └── {provider}/
│           └── {entity}/
│               └── {date}/          # YYYY-MM-DD
│                   ├── batch_001.jsonl.zst
│                   └── batch_002.jsonl.zst
├── silver/
│   └── {provider}/
│       └── {entity}/                # Delta Lake table
│           ├── _delta_log/
│           ├── part-00000-*.parquet
│           └── ...
├── gold/
│   └── {provider}/
│       └── {entity}/                # Delta Lake table (flattened)
│           ├── _delta_log/
│           └── ...
├── checkpoints/
│   └── {pipeline_name}/
│       └── checkpoint.json          # Last processed state
└── quarantine/
    └── common.quarantine/           # Unified quarantine table
        ├── _delta_log/
        └── ...
```

## Layer Details

### Bronze Layer

| Aspect | Value |
|--------|-------|
| Format | JSONL + zstd compression |
| Path Pattern | `data/bronze/v1/{provider}/{entity}/{date}/` |
| Retention | 90 days (manual cleanup) |
| Idempotency | Append-only |

**Example paths:**
```
data/bronze/v1/chembl/activity/2025-01-15/batch_001.jsonl.zst
data/bronze/v1/pubchem/compound/2025-01-15/batch_001.jsonl.zst
```

### Silver Layer

| Aspect | Value |
|--------|-------|
| Format | Delta Lake (delta-rs) |
| Path Pattern | `data/silver/{provider}/{entity}/` |
| Retention | Permanent |
| Idempotency | Merge/Upsert by `content_hash` |

**Key characteristics:**
- ACID transactions via Delta Lake
- Contains full JSON fields for forensic analysis
- Time travel available via `version` parameter

**Reading Silver data:**
```python
import polars as pl

# Current version
df = pl.read_delta("data/silver/chembl/activity")

# Historical version (time travel)
df = pl.read_delta("data/silver/chembl/activity", version=5)
```

### Gold Layer

| Aspect | Value |
|--------|-------|
| Format | Delta Lake (flattened schema) |
| Path Pattern | `data/gold/{provider}/{entity}/` |
| Retention | Permanent |
| Idempotency | SCD Type 2 or partition overwrite |

**Key characteristics:**
- Flattened structure (no nested JSON)
- Excludes fields from `GOLD_EXCLUDE_FIELDS`
- Optimized for analytics queries

### Checkpoints

| Aspect | Value |
|--------|-------|
| Format | JSON |
| Path Pattern | `data/checkpoints/{pipeline}/checkpoint.json` |
| Purpose | Resume interrupted pipelines |

**Checkpoint structure:**
```json
{
  "last_processed_id": "CHEMBL12345",
  "last_processed_ts": "2025-01-15T10:30:00Z",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_count": 42
}
```

## Atomic Writes

All file writes use atomic patterns to prevent data corruption:

1. Write to temporary file (`.tmp` suffix)
2. Fsync to ensure durability
3. Atomic rename to final path

See `src/bioetl/infrastructure/storage/_atomic.py` for implementation.

## Maintenance Operations

### VACUUM (Weekly)

Remove old Delta Lake files:

```bash
# Via Python
python -c "
from deltalake import DeltaTable
dt = DeltaTable('data/silver/chembl/activity')
dt.vacuum(retention_hours=168)  # 7 days
"
```

### Checkpoint Cleanup

After successful pipeline completion, checkpoints are automatically deleted.
For manual cleanup:

```bash
rm -rf data/checkpoints/{pipeline}/
```

### Quarantine Purge

```bash
make quarantine-purge PIPELINE=chembl_activity
```

## Configuration

Storage paths are configured via environment variables or `Settings`:

```python
from bioetl.infrastructure.config import Settings

settings = Settings()
print(settings.data_dir)  # Path("data")
print(settings.bronze_path)  # Path("data/bronze")
print(settings.silver_path)  # Path("data/silver")
```

## Migration from S3

If migrating from a previous S3-based deployment:

1. Download S3 data: `aws s3 sync s3://bioetl-bronze/ data/bronze/`
2. Update environment: Remove `AWS_*` variables
3. Reinstall: `pip install -e .[dev]`

See [ADR-010 Migration Notes](../02-architecture/decisions/ADR-010-local-only-deployment.md#migration-notes).
