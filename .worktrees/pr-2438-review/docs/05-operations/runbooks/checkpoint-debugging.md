# Checkpoint Debugging Runbook

## Overview

Checkpoints track pipeline progress to enable resumable execution. This runbook covers troubleshooting checkpoint-related issues.

## Checkpoint Location

```
data/checkpoints/{provider}-{entity}.json
```

Example: `data/checkpoints/chembl_activity.json`

## Checkpoint Structure

```json
{
  "provider": "chembl",
  "entity": "activity",
  "last-offset": 1500000,
  "last-run-id": "run-20260102-143022-abc123",
  "last-run-timestamp": "2026-01-02T14:30:22.123456Z",
  "last-run-type": "incremental",
  "total-records-processed": 1500000,
  "schema-version": "1.0.0"
}
```

## Common Issues

### Issue 1: Pipeline Skips Records

**Symptom**: Pipeline completes but some records are missing.

**Diagnosis**:
```bash
# Check checkpoint offset
cat data/checkpoints/chembl_activity.json | jq '.last-offset'

# Compare with source record count
# (provider-specific, example for ChEMBL)
curl "https://www.ebi.ac.uk/chembl/api/data/activity?limit=1" | jq '.page-meta.total-count'
```

**Resolution**:
1. If checkpoint offset > source count: Reset checkpoint
2. If checkpoint offset < expected: Resume should catch up
3. If records missing within processed range: Full refresh needed

### Issue 2: Duplicate Records

**Symptom**: Same records appearing multiple times in Silver.

**Diagnosis**:
```python
import polars as pl
from deltalake import DeltaTable

dt = DeltaTable("data/output/silver/chembl/activity")
df = pl.scan-delta(str(dt)).collect()

# Check for duplicates
duplicates = df.group-by("activity-id").count().filter(pl.col("count") > 1)
print(f"Duplicate records: {len(duplicates)}")
```

**Resolution**:
1. Check if checkpoint was manually modified
2. Verify content-hash is being calculated correctly
3. Run deduplication:
   ```bash
   bioetl dedupe --table chembl_activity
   ```

### Issue 3: Checkpoint Corruption

**Symptom**: JSON parse errors, invalid values.

**Diagnosis**:
```bash
# Validate JSON
python -m json.tool data/checkpoints/chembl_activity.json

# Check file permissions
ls -la data/checkpoints/
```

**Resolution**:
1. If partially written: Restore from backup
2. If no backup: Reset checkpoint (full refresh required)

```bash
# Backup corrupted checkpoint
mv data/checkpoints/chembl_activity.json data/checkpoints/chembl_activity.json.corrupted

# Create fresh checkpoint (optional, will be created on first run)
echo '{}' > data/checkpoints/chembl_activity.json
```

### Issue 4: Checkpoint Not Updating

**Symptom**: Pipeline runs but checkpoint offset doesn't change.

**Diagnosis**:
```bash
# Check file modification time
stat data/checkpoints/chembl_activity.json

# Verify write permissions
touch data/checkpoints/test && rm data/checkpoints/test
```

**Resolution**:
1. Check file system permissions
2. Check for disk full condition
3. Verify checkpoint port is correctly injected

### Issue 5: Wrong Offset After Schema Change

**Symptom**: Pipeline processes old records after schema evolution.

**Diagnosis**:
1. Check checkpoint schema-version
2. Compare with current schema version in code

**Resolution**:
If schema version mismatch is intentional:
```bash
# Full refresh with new schema
bioetl run --pipeline chembl_activity --run-type rebuild
```

## Manual Checkpoint Operations

### View Checkpoint

```bash
cat data/checkpoints/chembl_activity.json | python -m json.tool
```

### Reset Checkpoint

```bash
# Backup first
cp data/checkpoints/chembl_activity.json data/checkpoints/chembl_activity.json.bak

# Reset to beginning
echo '{"provider": "chembl", "entity": "activity", "last-offset": 0}' > data/checkpoints/chembl_activity.json
```

### Set Specific Offset

```python
import json

checkpoint-path = "data/checkpoints/chembl_activity.json"

with open(checkpoint-path) as f:
    checkpoint = json.load(f)

# Set to specific offset
checkpoint["last-offset"] = 1000000
checkpoint["last-run-type"] = "manual-reset"

with open(checkpoint-path, "w") as f:
    json.dump(checkpoint, f, indent=2)
```

### Clear All Checkpoints

```bash
# Backup first!
mkdir -p data/checkpoints.bak
cp data/checkpoints/*.json data/checkpoints.bak/

# Clear all
rm data/checkpoints/*.json
```

## Checkpoint Integrity Checks

### Validate Checkpoint Consistency

```python
import json
from pathlib import Path
from deltalake import DeltaTable

def validate-checkpoint(provider: str, entity: str):
    """Validate checkpoint against Silver table state."""

    checkpoint-path = Path(f"data/output/checkpoints/{provider}-{entity}.json")
    table-path = Path(f"data/output/silver/{provider}/{entity}")

    # Load checkpoint
    with open(checkpoint-path) as f:
        checkpoint = json.load(f)

    # Load table
    dt = DeltaTable(str(table-path))
    row-count = dt.to-pyarrow-table().num-rows

    print(f"Checkpoint offset: {checkpoint.get('last-offset', 0)}")
    print(f"Table row count: {row-count}")

    # Check consistency
    if checkpoint.get("total-records-processed", 0) != row-count:
        print("WARNING: Checkpoint and table row count mismatch!")
        return False

    print("Checkpoint is consistent with table state.")
    return True

# Validate
validate-checkpoint("chembl", "activity")
```

## Backup and Recovery

### Automated Backup

Checkpoints are backed up before each run:
```
data/checkpoints/chembl_activity.json.bak
```

### Manual Backup

```bash
# Timestamp-based backup
cp data/checkpoints/chembl_activity.json \
   data/checkpoints/chembl_activity.$(date +%Y%m%d-%H%M%S).json
```

### Recovery from Backup

```bash
# List available backups
ls -la data/checkpoints/*.bak data/checkpoints/*.json.*

# Restore from backup
cp data/checkpoints/chembl_activity.json.bak data/checkpoints/chembl_activity.json
```

## Monitoring

Key metrics to track:
- Checkpoint offset progression
- Time since last successful update
- Mismatch between checkpoint and table state

Alert on:
- Checkpoint not updated for > 24 hours
- Checkpoint offset decreases (potential corruption)
- File permission errors
