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
bioetl checkpoint inspect --pipeline chembl_activity --manifest-id "$MANIFEST_ID"
bioetl checkpoint inspect --pipeline chembl_activity --run-id "$RUN_ID"
bioetl run --pipeline chembl_activity --resume-run-id "$RUN_ID"
bioetl run --pipeline chembl_activity --resume-manifest-id "$MANIFEST_ID"
bioetl checkpoint inspect --pipeline chembl_activity --run-id "$RUN_ID" --format json
bioetl checkpoint audit-run --run-id "$RUN_ID"
```

The text and JSON payloads expose:

- checkpoint anchors: `manifest_id`, `execution_fingerprint`,
  `effective_config_hash`, `effective_config_artifact_id`, contract refs, and
  DQ compatibility hash;
- replay taxonomy: `exact_replay`, `checkpoint_snapshot_only_resume`,
  `checkpoint_snapshot_plus_ledger_suffix_resume`,
  `full_scan_idempotent_rebuild`, `rebuild_only`, `blocked_resume`,
  `missing_checkpoint`, `missing_run_manifest`, or
  `corrupted_checkpoint_payload`;
- replay context details: `replay_mode`, `continuation_mode`,
  `operator_replay_mode`, and `replay_readiness_verdict` so operators can see
  whether a compatible checkpoint is ordinary resume, bounded composite
  lifecycle reconstruction, or exact replay;
- anchor diff lists: matched, mismatched, and missing checkpoint-vs-manifest
  anchors.

For ordinary pipelines, `--resume` still means "follow the latest checkpoint
pointer", while `--resume-run-id` / `--resume-manifest-id` means "pin resume to
this exact checkpoint occurrence and then apply the same compatibility gates".

Examples:

- `compatibility_taxonomy: exact_replay` means the checkpoint anchors match a
  manifest that is `exact_replay_supported` and exact replay was requested.
- `compatibility_taxonomy: checkpoint_snapshot_only_resume` means resume is
  compatible on the ordinary checkpoint path, but the run must not be described
  as exact replay.
- `compatibility_taxonomy: checkpoint_snapshot_plus_ledger_suffix_resume` means
  the compatible path is the bounded composite checkpoint snapshot +
  ledger-suffix reconstruction model; diagnostics then determine whether the
  persisted evidence supports only lifecycle reconstruction or the richer
  composite payload projection.
- `compatibility_replay_readiness_verdict: lifecycle_projection_only` applies
  only when the ledger lacks the published rich composite replay payload
  evidence; runs with that evidence surface a regular resume-compatible verdict
  instead of the lifecycle-only warning.
- if checkpoint resume fails with unsupported ledger-suffix replay entries,
  treat that as a projector coverage conflict rather than as a transient cache
  miss; the bounded composite projector intentionally fails closed when suffix
  events fall outside its published contract.
- `compatibility_taxonomy: blocked_resume` means one or more execution identity
  anchors differ; do not resume until the mismatch is explained.
- `compatibility_taxonomy: missing_run_manifest` or
  `corrupted_checkpoint_payload` means evidence is incomplete or corrupt and
  must not be collapsed into a normal cache miss.

### Reference: resume anchor validation

Composite checkpoint resume validation is implemented in
`src/bioetl/application/composite/checkpoint/_load_validation.py` and is the
reference fail-closed pattern for replay-critical checkpoint gates.

The validator compares the persisted checkpoint state with the current expected
runtime anchors:

- `contract_ref`
- `contract_version`
- `effective_config_hash`
- `effective_config_artifact_id`
- `execution_fingerprint`
- `dq_contract_compatibility_hash`
- `input_snapshot_fingerprint`
- `manifest_id`
- `composite_run_identity`

If an expected anchor is present but the checkpoint omits it, resume is blocked.
If both sides carry an anchor and values differ, resume is blocked. The emitted
diagnostic uses `reason_code=checkpoint_resume_incompatible` and the runner
raises `CheckpointConflictError`.

For composite resume, checkpoint state remains the trusted operational baseline.
Only after anchors pass does the runtime apply bounded run-ledger suffix replay
strictly after the checkpoint watermark. That suffix replay restores lifecycle
milestones and replay watermark metadata only; it does not reconstruct rich
checkpoint payloads such as dependency result maps, enrichment result maps, or
merge payload details.

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
