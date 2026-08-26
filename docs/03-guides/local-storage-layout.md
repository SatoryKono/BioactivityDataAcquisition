______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-26'

______________________________________________________________________

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
    │               ├── batch-{date}-{batch-id}.jsonl.zst
    │               ├── batch-{date}-{batch-id}.jsonl     # Optional JSON copy
    │               ├── {provider}-{entity}-metadata.yaml # Optional metadata
    │               └── batch-{date}-{provider}-{entity}-dq-report.json
    ├── silver/
    │   └── {provider}/
    │       └── {entity}/                # Delta Lake table
    │           ├── _delta_log/
    │           ├── part-00000-*.parquet
    │           ├── {provider}-{entity}-metadata.yaml
    │           └── silver-{provider}-{entity}-dq-report.json
    ├── gold/
    │   └── {provider}/
    │       └── {entity}/                # Delta Lake table (flattened)
    │           ├── _delta_log/
    │           ├── part-00000-*.parquet
    │           ├── {provider}-{entity}-metadata.yaml
    │           └── gold-{provider}-{entity}-dq-report.json
    ├── control/                         # ADR-044 / ADR-047 control plane
    │   ├── run_manifest/
    │   ├── run_ledger/
    │   ├── workflow_manifest/
    │   ├── workflow_ledger/
    │   ├── workflow_state/
    │   └── workflow_transform_results/
    ├── checkpoints/
    │   ├── {pipeline-name}.json         # Flat structure (e.g., chembl_activity.json)
    │   └── composite/
    │       └── composite-{name}-{run-id}.json
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

| Aspect       | Value                                            |
| ------------ | ------------------------------------------------ |
| Format       | JSONL + zstd compression                         |
| Path Pattern | `data/output/bronze/{provider}/{entity}/{date}/` |
| File Pattern | `batch-{YYYY-MM-DD}-{batch-id}.jsonl.zst`        |
| Retention    | 90 days (manual cleanup)                         |
| Idempotency  | Append-only                                      |

**Example paths:**

```
data/output/bronze/chembl/activity/2025-01-15/batch-2025-01-15-a1b2c3d4.jsonl.zst
data/output/bronze/pubchem/compound/2025-01-15/batch-2025-01-15-e5f6g7h8.jsonl.zst
```

**Sidecar files (optional):**

- `{provider}-{entity}-metadata.yaml` - Batch metadata (record counts, timestamps)
- `batch-{date}-{provider}-{entity}-dq-report.json` - Data quality report

### Silver Layer

| Aspect       | Value                                     |
| ------------ | ----------------------------------------- |
| Format       | Delta Lake (delta-rs)                     |
| Path Pattern | `data/output/silver/{provider}/{entity}/` |
| Retention    | Permanent                                 |
| Idempotency  | Merge/Upsert by `content-hash`            |

**Key characteristics:**

- ACID transactions via Delta Lake
- Contains full JSON fields for forensic analysis
- Time travel available via `version` parameter

**Sidecar files:**

- `{provider}-{entity}-metadata.yaml` - Table metadata with lineage
- `silver-{provider}-{entity}-dq-report.json` - Data quality report

**Reading Silver data:**

```python
import polars as pl

# Current version
df = pl.read_delta("data/output/silver/chembl/activity")

# Historical version (time travel)
df = pl.read_delta("data/output/silver/chembl/activity", version=5)
```

### Gold Layer

| Aspect       | Value                                   |
| ------------ | --------------------------------------- |
| Format       | Delta Lake (flattened schema)           |
| Path Pattern | `data/output/gold/{provider}/{entity}/` |
| Retention    | Permanent                               |
| Idempotency  | SCD Type 2 or partition overwrite       |

**Key characteristics:**

- Flattened structure (no nested JSON)
- Excludes fields from `GOLD-EXCLUDE-FIELDS`
- Optimized for analytics queries

**Sidecar files:**

- `{provider}-{entity}-metadata.yaml` - Table metadata with SCD info
- `gold-{provider}-{entity}-dq-report.json` - Data quality report

### Checkpoints

| Aspect            | Value                                                              |
| ----------------- | ------------------------------------------------------------------ |
| Format            | JSON                                                               |
| Path Pattern      | `data/output/checkpoints/{pipeline-name}.json`                     |
| Composite Pattern | `data/output/checkpoints/composite/composite-{name}-{run-id}.json` |
| Purpose           | Resume interrupted pipelines                                       |

**Flat structure** (not nested):

```
	data/output/checkpoints/
	├── chembl_activity.json
	├── chembl_molecule.json
	├── pubchem_compound.json
	└── composite_publication.json
```

Checkpoint files use a flat layout: `data/output/checkpoints/{pipeline}.json`.

**Checkpoint structure:**

```json
{
  "pipeline": "chembl_activity",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "records_processed": 4200
  },
  "version": "2.0"
}
```

Checkpoint resume is offset-based. Pipelines with `loading_strategy: full_scan_only`
ignore checkpoint resume even when `--resume` is passed.

## Atomic Writes

All file writes use atomic patterns to prevent data corruption:

1. Write to temporary file (`.tmp` suffix)
1. Fsync to ensure durability
1. Atomic rename to final path

See `src/bioetl/infrastructure/storage/support/atomic_ops.py` for implementation.

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
For manual cleanup after the owning process has stopped and you intentionally want
to discard resume state:

```bash
rm data/output/checkpoints/{pipeline-name}.json
```

### Quarantine Purge

```bash
bioetl quarantine purge --pipeline chembl_activity --older-than-days 30 --dry-run
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

Strict reproducibility contexts do not accept implicit fallback roots. When
`--exact-replay` or a strict persistence profile is active, `settings.data_dir`
must be configured explicitly; repo-default `data/`, private-cache, and `/tmp`
resolution remain degraded-mode conveniences only.

### Convention-Based Path Resolution

Pipeline configurations can omit explicit paths. The canonical config pipeline automatically
resolves paths using conventions:

```yaml
# configs/entities/chembl/activity.yaml
sink:
  bronze:
    # path defaults to: data/output/bronze/chembl/activity
  silver:
    # path defaults to: data/output/silver/chembl/activity
  gold:
    # path defaults to: data/output/gold/chembl/activity
```

**Resolution logic** (`src/bioetl/infrastructure/config/pipeline_payload_normalization.py`):

```python
layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")
```

This convention ensures consistent paths across all pipelines without repetitive
configuration. Explicit paths can still be specified to override the defaults.

## Configs Structure

*Reference: [ADR-039: Unified Entity Config Format](../02-architecture/decisions/ADR-039-unified-entity-config-format.md)*

```text
configs/
├── base/
│   ├── pipeline.yaml
│   ├── quality.yaml
│   ├── bronze_fixture_manifest.yaml
│   └── bronze_fixture_gaps.yaml
├── providers/
│   ├── chembl.yaml
│   ├── crossref.yaml
│   ├── openalex.yaml
│   ├── pubchem.yaml
│   ├── pubmed.yaml
│   ├── semanticscholar.yaml
│   └── uniprot.yaml
├── entities/
│   ├── chembl/
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── assay_parameters.yaml
│   │   ├── cell_line.yaml
│   │   ├── compound_record.yaml
│   │   ├── molecule.yaml
│   │   ├── protein_class.yaml
│   │   ├── publication.yaml
│   │   ├── publication_similarity.yaml
│   │   ├── publication_term.yaml
│   │   ├── subcellular_fraction.yaml
│   │   ├── target.yaml
│   │   ├── target_component.yaml
│   │   └── tissue.yaml
│   ├── crossref/publication.yaml
│   ├── openalex/publication.yaml
│   ├── pubchem/compound.yaml
│   ├── pubmed/publication.yaml
│   ├── semanticscholar/publication.yaml
│   └── uniprot/{idmapping,protein}.yaml
├── composites/
│   ├── activity.yaml
│   ├── assay.yaml
│   ├── molecule.yaml
│   ├── publication.yaml
│   ├── target.yaml
│   └── field_groups/publication.yaml
├── enums/
│   └── chembl.yaml
└── naming_exceptions.yaml
```

### Unified Config Layers

| Layer            | Path                                        | Purpose                                                   |
| ---------------- | ------------------------------------------- | --------------------------------------------------------- |
| Global defaults  | `configs/base/*.yaml`                       | Common runtime and DQ defaults                            |
| Provider config  | `configs/providers/{provider}.yaml`         | Provider endpoint/auth/rate-limit settings                |
| Entity config    | `configs/entities/{provider}/{entity}.yaml` | Unified pipeline + schema + quality + filters + contracts |
| Composite config | `configs/composites/{entity}.yaml`          | Multi-provider enrichment orchestration                   |

For details, see [DQ Configuration Guide](dq-configuration.md) and [Pipeline Configuration Guide](pipeline-configuration.md).

### Fixture Governance Artifacts

- `configs/base/bronze_fixture_manifest.yaml`:
  positive inventory of tracked CI Bronze samples.
- `configs/base/bronze_fixture_gaps.yaml`:
  explicit exceptions for pipelines that still lack tracked fixtures.

This separation allows deterministic CI coverage while keeping unfinished
pipelines visible and actionable.

## Migration from S3

If migrating from a previous S3-based deployment:

1. Download S3 data: `aws s3 sync s3://bioetl-bronze/ data/output/bronze/`
1. Update environment: Remove `AWS-*` variables
1. Reinstall: `pip install -e .[dev]`

See [ADR-010 Migration Notes](../02-architecture/decisions/ADR-010-local-only-deployment.md#migration-notes).
