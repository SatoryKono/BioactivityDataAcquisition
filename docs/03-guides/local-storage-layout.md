# Local Storage Layout

*Reference: [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

This guide describes the local filesystem layout used by BioETL in Local-Only mode.

## Directory Structure

```
data/
└── output/                              # Data output directory (ADR-025)
    ├── bronze/
    │   └── {provider}/
    │       └── {entity}/
    │           └── {date}/              # YYYY-MM-DD
    │               ├── batch_{date}_{batch_id}.jsonl.zst
    │               ├── batch_{date}_{batch_id}.jsonl     # Optional JSON copy
    │               ├── {provider}_{entity}_metadata.yaml # Optional metadata
    │               └── batch_{date}_{provider}_{entity}_dq_report.json
    ├── silver/
    │   └── {provider}/
    │       └── {entity}/                # Delta Lake table
    │           ├── _delta_log/
    │           ├── part-00000-*.parquet
    │           ├── {provider}_{entity}_metadata.yaml
    │           └── silver_{provider}_{entity}_dq_report.json
    ├── gold/
    │   └── {provider}/
    │       └── {entity}/                # Delta Lake table (flattened)
    │           ├── _delta_log/
    │           ├── part-00000-*.parquet
    │           ├── {provider}_{entity}_metadata.yaml
    │           └── gold_{provider}_{entity}_dq_report.json
    ├── checkpoints/
    │   ├── {pipeline_name}.json         # Flat structure (e.g., chembl_activity.json)
    │   └── composite/
    │       └── composite_{name}_{run_id}.json
    ├── quarantine/
    │   └── common.quarantine/           # Unified quarantine table
    │       ├── _delta_log/
    │       └── part-00000-*.parquet
    └── reports/
        └── dq/                          # Composite DQ reports
```

> **Note**: The `output/` subdirectory separates generated data from configuration
> and input files. This structure is established by ADR-025 and used by all
> pipeline configurations.

## Layer Details

### Bronze Layer

| Aspect | Value |
|--------|-------|
| Format | JSONL + zstd compression |
| Path Pattern | `data/output/bronze/{provider}/{entity}/{date}/` |
| File Pattern | `batch_{YYYY-MM-DD}_{batch_id}.jsonl.zst` |
| Retention | 90 days (manual cleanup) |
| Idempotency | Append-only |

**Example paths:**
```
data/output/bronze/chembl/activity/2025-01-15/batch_2025-01-15_a1b2c3d4.jsonl.zst
data/output/bronze/pubchem/compound/2025-01-15/batch_2025-01-15_e5f6g7h8.jsonl.zst
```

**Sidecar files (optional):**
- `{provider}_{entity}_metadata.yaml` - Batch metadata (record counts, timestamps)
- `batch_{date}_{provider}_{entity}_dq_report.json` - Data quality report

### Silver Layer

| Aspect | Value |
|--------|-------|
| Format | Delta Lake (delta-rs) |
| Path Pattern | `data/output/silver/{provider}/{entity}/` |
| Retention | Permanent |
| Idempotency | Merge/Upsert by `content_hash` |

**Key characteristics:**
- ACID transactions via Delta Lake
- Contains full JSON fields for forensic analysis
- Time travel available via `version` parameter

**Sidecar files:**
- `{provider}_{entity}_metadata.yaml` - Table metadata with lineage
- `silver_{provider}_{entity}_dq_report.json` - Data quality report

**Reading Silver data:**
```python
import polars as pl

# Current version
df = pl.read_delta("data/output/silver/chembl/activity")

# Historical version (time travel)
df = pl.read_delta("data/output/silver/chembl/activity", version=5)
```

### Gold Layer

| Aspect | Value |
|--------|-------|
| Format | Delta Lake (flattened schema) |
| Path Pattern | `data/output/gold/{provider}/{entity}/` |
| Retention | Permanent |
| Idempotency | SCD Type 2 or partition overwrite |

**Key characteristics:**
- Flattened structure (no nested JSON)
- Excludes fields from `GOLD_EXCLUDE_FIELDS`
- Optimized for analytics queries

**Sidecar files:**
- `{provider}_{entity}_metadata.yaml` - Table metadata with SCD info
- `gold_{provider}_{entity}_dq_report.json` - Data quality report

### Checkpoints

| Aspect | Value |
|--------|-------|
| Format | JSON |
| Path Pattern | `data/output/checkpoints/{pipeline_name}.json` |
| Composite Pattern | `data/output/checkpoints/composite/composite_{name}_{run_id}.json` |
| Purpose | Resume interrupted pipelines |

**Flat structure** (not nested):
```
data/output/checkpoints/
├── chembl_activity.json
├── chembl_molecule.json
├── pubchem_compound.json
└── composite/
    └── composite_publication_enrichment_abc123.json
```

**Checkpoint structure:**
```json
{
  "pipeline": "chembl_activity",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "last_processed_id": "CHEMBL12345",
    "last_processed_ts": "2025-01-15T10:30:00Z",
    "batch_count": 42
  },
  "version": "2.0"
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
dt = DeltaTable('data/output/silver/chembl/activity')
dt.vacuum(retention_hours=168)  # 7 days
"
```

### Checkpoint Cleanup

After successful pipeline completion, checkpoints are automatically deleted.
For manual cleanup:

```bash
rm data/output/checkpoints/{pipeline_name}.json
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
# Actual paths use data/output/ hierarchy:
# - Bronze: data/output/bronze/
# - Silver: data/output/silver/
# - Gold: data/output/gold/
```

### Convention-Based Path Resolution

Pipeline configurations can omit explicit paths. The config loader automatically
resolves paths using conventions:

```yaml
# configs/pipelines/chembl/activity.yaml
sink:
  bronze:
    # path defaults to: data/output/bronze/chembl/activity
  silver:
    # path defaults to: data/output/silver/chembl/activity
  gold:
    # path defaults to: data/output/gold/chembl/activity
```

**Resolution logic** (`src/bioetl/infrastructure/config_loader.py`):
```python
layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")
```

This convention ensures consistent paths across all pipelines without repetitive
configuration. Explicit paths can still be specified to override the defaults.

## Configs Structure

*Reference: [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)*

```
configs/
├── dq/                                # DQ Configuration Hierarchy (ADR-027)
│   ├── _defaults.yaml                 # Global defaults (thresholds, common validations)
│   ├── providers/
│   │   ├── chembl.yaml                # ChEMBL provider overrides
│   │   ├── pubchem.yaml               # PubChem provider overrides
│   │   └── uniprot.yaml               # UniProt provider overrides
│   └── entities/
│       ├── chembl/
│       │   ├── activity.yaml          # Activity-specific rules
│       │   ├── assay.yaml
│       │   ├── molecule.yaml
│       │   └── target.yaml
│       ├── pubchem/
│       │   └── compound.yaml
│       └── uniprot/
│           └── target.yaml
│
├── pipelines/                         # Pipeline orchestration configs
│   ├── _defaults.yaml                 # Base pipeline defaults
│   ├── chembl/
│   │   ├── activity.yaml              # References dq_config_file
│   │   ├── assay.yaml
│   │   ├── molecule.yaml
│   │   └── target.yaml
│   ├── pubchem/
│   │   └── compound.yaml
│   └── uniprot/
│       └── target.yaml
│
├── sources/                           # Source connection configs
│   ├── chembl.yaml
│   ├── pubchem.yaml
│   └── uniprot.yaml
│
└── env/
    └── .env.example
```

### DQ Config Hierarchy

| Level | Path | Purpose |
|-------|------|---------|
| Global | `dq/_defaults.yaml` | Base thresholds (0.05/0.20), common validations |
| Provider | `dq/providers/{provider}.yaml` | Provider-specific overrides |
| Entity | `dq/entities/{provider}/{entity}.yaml` | Entity-specific rules |

**Merge order**: defaults → provider → entity → inline overrides

See [DQ Configuration Guide](dq-configuration.md) for details.

## Migration from S3

If migrating from a previous S3-based deployment:

1. Download S3 data: `aws s3 sync s3://bioetl-bronze/ data/bronze/`
2. Update environment: Remove `AWS_*` variables
3. Reinstall: `pip install -e .[dev]`

See [ADR-010 Migration Notes](../02-architecture/decisions/ADR-010-local-only-deployment.md#migration-notes).
