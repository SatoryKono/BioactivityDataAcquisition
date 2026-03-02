# Checkpoint Debugging Runbook

*Reference: [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Checkpoints are local files under `data/output/checkpoints/`.

## Overview

Checkpoints store resume state for each pipeline.
Use this runbook to inspect, reset, and recover checkpoint files.

## Checkpoint Location

```text
data/output/checkpoints/{pipeline}.json
```

Example: `data/output/checkpoints/chembl_activity.json`

## Checkpoint Structure

Actual local checkpoint format:

```json
{
  "pipeline": "chembl_activity",
  "run_id": "260bb657-2682-405f-8939-900428097071",
  "metadata": {
    "records_processed": 1500000
  },
  "version": "2.0"
}
```

## Common Issues

### Issue 1: Resume starts from unexpected position

**Symptom**: `--resume` starts too early or too late.

**Diagnosis**:

```bash
# Inspect checkpoint payload
cat data/output/checkpoints/chembl_activity.json | jq

# Check processed counter used for resume metadata
cat data/output/checkpoints/chembl_activity.json | jq '.metadata.records_processed'
```

**Resolution**:

1. If value is stale/corrupt, backup and reset checkpoint.
2. If state is valid but data is inconsistent, run full rebuild:

```bash
bioetl run --pipeline chembl_activity --run-type rebuild
```

### Issue 2: Checkpoint file is missing

**Symptom**: `--resume` does not resume and starts from beginning.

**Diagnosis**:

```bash
ls -la data/output/checkpoints/
```

**Resolution**:

1. This is expected after successful runs (checkpoint is cleaned up).
2. If pipeline crashed and file is still missing, rerun without `--resume` or recover from backup.

### Issue 3: Checkpoint corruption

**Symptom**: JSON parse errors while loading checkpoint.

**Diagnosis**:

```bash
python -m json.tool data/output/checkpoints/chembl_activity.json
```

**Resolution**:

```bash
# Backup corrupted file
mv data/output/checkpoints/chembl_activity.json \
   data/output/checkpoints/chembl_activity.json.corrupted

# Recreate minimal valid checkpoint payload (optional)
echo '{"pipeline":"chembl_activity","run_id":"00000000-0000-0000-0000-000000000000","metadata":{"records_processed":0},"version":"2.0"}' \
  > data/output/checkpoints/chembl_activity.json
```

### Issue 4: File not updating

**Symptom**: Pipeline runs but checkpoint timestamp does not change.

**Diagnosis**:

```bash
stat data/output/checkpoints/chembl_activity.json

touch data/output/checkpoints/.write-test && rm data/output/checkpoints/.write-test
```

**Resolution**:

1. Verify filesystem permissions.
2. Verify available disk space.
3. Verify run is actually in incremental mode and checkpoint saving is reached.

## Manual Operations

### View checkpoint

```bash
cat data/output/checkpoints/chembl_activity.json | python -m json.tool
```

### Backup checkpoint

```bash
cp data/output/checkpoints/chembl_activity.json \
   data/output/checkpoints/chembl_activity.$(date +%Y%m%d-%H%M%S).json
```

### Reset one checkpoint

```bash
cp data/output/checkpoints/chembl_activity.json \
   data/output/checkpoints/chembl_activity.json.bak

rm -f data/output/checkpoints/chembl_activity.json
```

### Clear all checkpoints

```bash
mkdir -p data/output/checkpoints.bak
cp data/output/checkpoints/*.json data/output/checkpoints.bak/ 2>/dev/null || true
rm -f data/output/checkpoints/*.json
```

## Integrity Check Script

```python
import json
from pathlib import Path


def validate_checkpoint(pipeline: str) -> bool:
    checkpoint_path = Path(f"data/output/checkpoints/{pipeline}.json")
    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_path}")
        return False

    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    required_keys = {"pipeline", "run_id", "metadata", "version"}
    missing = required_keys - set(data.keys())
    if missing:
        print(f"Missing keys: {sorted(missing)}")
        return False

    records_processed = data.get("metadata", {}).get("records_processed")
    print(f"pipeline={data.get('pipeline')}")
    print(f"run_id={data.get('run_id')}")
    print(f"records_processed={records_processed}")
    print(f"version={data.get('version')}")
    return True


validate_checkpoint("chembl_activity")
```

## Monitoring Recommendations

Track and alert on:

- checkpoint file load failures
- repeated resume from same `records_processed` value
- missing checkpoint after abnormal termination
- write/permission errors in `data/output/checkpoints/`
