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

# Backfill and Rebuild Operations

## Trigger

- Run this procedure for controlled backfills or rebuilds of previously processed data.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Definitions

- **Backfill**: Loading historical data for a specific period.
- **Rebuild**: Completely clearing Silver/Gold tables and reloading from source/Bronze.

### Prerequisites

- **Exclusive Lock**: These operations require an exclusive lock in local `MemoryLock` scope.
- **Downtime**: Incremental pipelines must be stopped or will be blocked.

### Procedure: Full Rebuild

1. **Stop Incremental Pipelines**:

- Ensure no incremental runs are scheduled.

1. **Run Rebuild**:

   ```bash
   bioetl run --pipeline {name} --run-type rebuild
   ```

- *Note: This will automatically clear Silver and Gold tables for this entity.*

1. **Verify Data**:

   - Check record counts in Silver/Gold.
   - Validate DQ metrics.

1. **Resume Incremental**:

- Enable scheduled incremental runs.

### Procedure: Backfill (Time Range)

1. **Determine Range**:

- Identify start and end dates for backfill.

1. **Run Backfill**:

   ```bash
   # Example: Backfill for Jan 2024
   bioetl run --pipeline {name} --run-type backfill
   ```

1. **Monitor Progress**:

- Watch logs for progress. Backfills can be long-running.

### Troubleshooting

- **LockAcquisitionError**: Another process holds the lock. Wait or investigate.
- **Memory Issues**: Backfills process large volumes. Watch for OOM. Reduce batch size if needed.

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
