______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P0/P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-08-21'

______________________________________________________________________

# Data Recovery Runbook

## Trigger

- Run this procedure after data corruption, accidental deletion, or recovery-point incidents affecting Bronze, Silver, or Gold assets.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P0/P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Scenario 1: Silver/Gold Data Corruption

- **Symptom**: Data in Silver or Gold layers is found to be incorrect, incomplete, or corrupted. The Bronze layer is intact.
- **Cause**: A bug in a transformation, incorrect business logic, or a failed merge operation.
- **Recovery Steps**:
  1. **Stop Pipelines**: Halt all pipelines that write to the affected tables to prevent further corruption.
  1. **Identify Blast Radius**: Determine which tables and partitions are affected.
  1. **Inspect Time Travel (read-only)**: If the issue was recent (within the
     VACUUM retention window, default 7 days), inspect a previous Delta version
     with the local delta-rs/Polars path. BioETL does **not** ship Spark SQL
     `RESTORE TABLE`.
     ```python
     import polars as pl

     # Historical snapshot (read-only). Example Silver path:
     df = pl.read_delta("data/output/silver/chembl/activity", version=5)
     ```
     Runtime helper: bioetl.infrastructure.storage.support.retention_time_travel.load_time_travel_table.
     VACUUM policy: [vacuum-procedures.md](vacuum-procedures.md).
  1. **Full Rebuild from Bronze**: The supported write-path recovery is rebuild
     from Bronze. Time-travel reads do not mutate Silver/Gold.
     - Delete the corrupted data from the Silver/Gold tables.
     - Run the pipeline with the `--run-type rebuild` flag. This will re-process all data from Bronze.
     ```bash
     bioetl run --pipeline <pipeline-name> --run-type rebuild
     ```

### Scenario 2: Bronze Data Loss or Corruption

- **Symptom**: Files in the Bronze layer (local storage) are deleted or corrupted.
- **Cause**: Accidental deletion, filesystem errors, or infrastructure failure.
- **Recovery Steps**:
  1. **Stop All Pipelines**: Immediately halt all data ingestion.
  1. **Restore Local Backup**:
     - Restore `data/output/bronze` from the latest backup or snapshot.
     - Verify the restore point is just before the incident occurred.
  1. **Rebuild Silver/Gold**: Once the Bronze layer is restored, follow the steps in **Scenario 1** to rebuild the downstream layers. A full rebuild is mandatory.

### Scenario 3: Lost Checkpoint

- **Symptom**: A pipeline was interrupted, but the checkpoint file was lost or corrupted. The pipeline warns about a "Stale checkpoint" on restart.
- **Cause**: Local checkpoint write failure, race condition, or manual error.
- **Recovery Steps**:
  1. **Option A (Safest)**: Delete the checkpoint and re-process from the beginning.
     ```bash
     # Delete the checkpoint file for the affected pipeline
     rm data/output/checkpoints/{pipeline-name}.json

     # Re-run the pipeline (will start from scratch)
     bioetl run --pipeline <pipeline-name> --run-type rebuild
     ```
     - **Note**: For checkpoint reset, delete the file at `data/output/checkpoints/{pipeline-name}.json`.
     - **Impact**: This may create duplicate records in the Bronze layer, but the merge/upsert logic in the Silver layer will handle deduplication, ensuring correctness.
  1. **Option B (Advanced)**: Manually determine the last successfully processed record ID or timestamp from the Silver table and create a new checkpoint file. This is faster but more error-prone.

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
