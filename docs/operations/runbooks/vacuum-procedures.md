# VACUUM Procedures Runbook

## Overview

Delta Lake tables accumulate old versions of data files for time travel and ACID transactions. VACUUM removes files older than the retention period to reclaim storage.

**Note**: VACUUM is automated after each successful pipeline run via `PostrunService`. This runbook covers manual VACUUM operations.

## When to Run Manual VACUUM

- After bulk data corrections
- When storage usage is unexpectedly high
- After schema evolution operations
- During scheduled maintenance windows

## Prerequisites

- Pipeline is **not running** (avoid conflicts)
- Sufficient disk space for temporary files
- Backup strategy in place

## Automatic VACUUM

VACUUM runs automatically after successful pipeline completion:

```python
# From postrun_service.py
await self.run_vacuum_if_enabled()
```

Configuration in pipeline YAML:
```yaml
storage:
  vacuum:
    enabled: true
    retention_hours: 168  # 7 days default
```

## Manual VACUUM Procedures

### Check Table Status

Before VACUUM, check current table state:

```python
from deltalake import DeltaTable

dt = DeltaTable("data/silver/chembl_activity")

# Get table info
print(f"Version: {dt.version()}")
print(f"Files: {len(dt.file_uris())}")
print(f"Protocol: {dt.protocol()}")

# Check file sizes
import os
total_size = sum(os.path.getsize(f) for f in dt.file_uris())
print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
```

### Run VACUUM

```python
from deltalake import DeltaTable
from datetime import timedelta

# Open table
dt = DeltaTable("data/silver/chembl_activity")

# Dry run first (shows files that would be deleted)
dt.vacuum(retention_hours=168, dry_run=True, enforce_retention_duration=False)

# Execute VACUUM (7 day retention)
dt.vacuum(retention_hours=168, dry_run=False, enforce_retention_duration=False)
```

**Warning**: `enforce_retention_duration=False` bypasses the 7-day safety check. Only use in controlled scenarios.

### VACUUM All Tables

```python
from pathlib import Path
from deltalake import DeltaTable

def vacuum_all_tables(base_path: str, retention_hours: int = 168):
    """VACUUM all Delta tables in directory."""
    base = Path(base_path)

    for table_dir in base.iterdir():
        if not table_dir.is_dir():
            continue
        if not (table_dir / "_delta_log").exists():
            continue

        print(f"Vacuuming: {table_dir.name}")
        dt = DeltaTable(str(table_dir))
        dt.vacuum(retention_hours=retention_hours, dry_run=False)
        print(f"  Version: {dt.version()}, Files: {len(dt.file_uris())}")

# Run for Silver tables
vacuum_all_tables("data/silver")

# Run for Gold tables
vacuum_all_tables("data/gold")
```

## OPTIMIZE Operations

In addition to VACUUM, consider running OPTIMIZE for query performance:

```python
from deltalake import DeltaTable

dt = DeltaTable("data/silver/chembl_activity")

# Compact small files
dt.optimize.compact()

# Z-order by frequently queried column
dt.optimize.z_order(columns=["molecule_chembl_id"])
```

## Retention Guidelines

| Table Type | Retention | Justification |
|------------|-----------|---------------|
| Bronze | 90 days | Archival, debugging |
| Silver | 7 days | Default, active queries |
| Gold | 7 days | Default, analytics |
| Critical | 30 days | Forensic/compliance |

## Troubleshooting

### VACUUM Hangs

If VACUUM takes too long:
1. Check for large number of files
2. Consider running in batches by version range
3. Increase retention to skip fewer files

### "Files still referenced" Error

Files may still be referenced if:
- Active readers are using old versions
- Time travel queries are running
- Retention period not exceeded

Solution: Wait for active operations to complete or increase retention.

### Storage Not Freed

After VACUUM, if storage isn't freed:
1. Check filesystem cache
2. Verify VACUUM completed successfully
3. Check for files outside Delta log management

## Monitoring

Track VACUUM metrics:
- Time to complete
- Files removed
- Storage reclaimed
- Table version after VACUUM

Log example:
```
INFO  | vacuum_completed | table=chembl_activity | files_removed=150 | bytes_freed=524288000 | duration_s=45.2
```

## Best Practices

1. **Schedule during low-usage periods**
2. **Always dry-run first** on production tables
3. **Monitor storage trends** to adjust retention
4. **Document VACUUM runs** in operations log
5. **Test time travel** after VACUUM to ensure required history preserved
