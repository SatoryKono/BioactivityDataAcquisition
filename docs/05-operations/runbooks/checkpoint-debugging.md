______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-03-30'

______________________________________________________________________

# Checkpoint Debugging Runbook

## Trigger

- Run this procedure when checkpoint state blocks resume, causes stale progress, or becomes inconsistent.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Overview

- Checkpoints store resume state for each pipeline. Use this runbook to inspect, reset, and recover checkpoint files.

### Checkpoint Location

```text
data/output/checkpoints/{pipeline}.json
```

- Example: `data/output/checkpoints/chembl_activity.json`

### Checkpoint Structure

- Actual local checkpoint format:

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

### Common Issues

### Issue 1: Resume starts from unexpected position

- **Symptom**: `--resume` starts too early or too late.

- **Diagnosis**:

```bash
# Inspect checkpoint payload
cat data/output/checkpoints/chembl_activity.json | jq

# Check processed counter used for resume metadata
cat data/output/checkpoints/chembl_activity.json | jq '.metadata.records_processed'
```

- **Resolution**:

1. If value is stale/corrupt, backup and reset checkpoint.
1. If state is valid but data is inconsistent, run full rebuild:

```bash
bioetl run --pipeline chembl_activity --run-type rebuild
```

### Issue 2: Checkpoint file is missing

- **Symptom**: `--resume` does not resume and starts from beginning.

- **Diagnosis**:

```bash
ls -la data/output/checkpoints/
```

- **Resolution**:

1. This is expected after successful runs (checkpoint is cleaned up).
1. If pipeline crashed and file is still missing, rerun without `--resume` or recover from backup.

### Issue 3: Checkpoint corruption

- **Symptom**: JSON parse errors while loading checkpoint.

- **Diagnosis**:

```bash
python -m json.tool data/output/checkpoints/chembl_activity.json
```

- **Resolution**:

```bash
# Backup corrupted file
mv data/output/checkpoints/chembl_activity.json \
   data/output/checkpoints/chembl_activity.json.corrupted

# Recreate minimal valid checkpoint payload (optional)
echo '{"pipeline":"chembl_activity","run_id":"00000000-0000-0000-0000-000000000000","metadata":{"records_processed":0},"version":"2.0"}' \
  > data/output/checkpoints/chembl_activity.json
```

### Issue 4: File not updating

- **Symptom**: Pipeline runs but checkpoint timestamp does not change.

- **Diagnosis**:

```bash
stat data/output/checkpoints/chembl_activity.json

touch data/output/checkpoints/.write-test && rm data/output/checkpoints/.write-test
```

- **Resolution**:

1. Verify filesystem permissions.
1. Verify available disk space.
1. Verify run is actually in incremental mode and checkpoint saving is reached.

### Manual Operations

### View checkpoint

```bash
cat data/output/checkpoints/chembl_activity.json | python -m json.tool
```

### View checkpoint with replay anchors

Use the workflow-backed CLI view before deciding whether a checkpoint can be
used for resume or exact replay:

```bash
bioetl checkpoint inspect --pipeline chembl_activity --run-id "$RUN_ID"
bioetl checkpoint inspect --pipeline chembl_activity --run-id "$RUN_ID" --format json
bioetl checkpoint audit-run --run-id "$RUN_ID"
```

The text and JSON payloads expose:

- checkpoint anchors: `manifest_id`, `execution_fingerprint`,
  `effective_config_hash`, `effective_config_artifact_id`, contract refs, and
  DQ compatibility hash;
- replay taxonomy: `exact_replay`, `resume_only`, `rebuild_only`,
  `compatible_resume`, `blocked_resume`, `missing_checkpoint`,
  `missing_run_manifest`, or `corrupted_checkpoint_payload`;
- anchor diff lists: matched, mismatched, and missing checkpoint-vs-manifest
  anchors.

Examples:

- `compatibility_taxonomy: exact_replay` means the checkpoint anchors match a
  manifest that is `exact_replay_supported` and exact replay was requested.
- `compatibility_taxonomy: resume_only` means resume is compatible, but the run
  must not be described as exact replay.
- `compatibility_taxonomy: blocked_resume` means one or more execution identity
  anchors differ; do not resume until the mismatch is explained.
- `compatibility_taxonomy: missing_run_manifest` or
  `corrupted_checkpoint_payload` means evidence is incomplete or corrupt and
  must not be collapsed into a normal cache miss.

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

### Integrity Check Script

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

### Monitoring Recommendations

- Track and alert on:

- checkpoint file load failures

- repeated resume from same `records_processed` value

- missing checkpoint after abnormal termination

- write/permission errors in `data/output/checkpoints/`

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
