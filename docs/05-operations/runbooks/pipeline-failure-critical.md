______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P0
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-03-30'

______________________________________________________________________

# Pipeline Failure: Critical Error (P0)

## Trigger

- Run this procedure for P0 pipeline failures that block critical execution or threaten data integrity.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P0.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Symptoms

- Pipeline crashes with exit code != 0.
- Logs contain `CRITICAL` level messages.
- Alert "Pipeline Failed" fires.
- `errors-total{type="critical"}` metric increments.

### Common Causes

1. **Infrastructure Failure**: Local storage unavailable, disk full, filesystem errors.
1. **Authentication Failure**: API key expired, invalid credentials.
1. **Schema Violation**: Source data structure changed significantly (Gold layer validation failed).
1. **Lock Acquisition Error**: Unable to acquire lock for `rebuild` or `backfill`.

### Diagnosis Steps

1. **Check Logs**:
   ```bash
   # Filter for CRITICAL errors
   grep "CRITICAL" logs/bioetl.log | jq .
   ```
1. **Identify Error Type**:
   - `AuthFailureError`: See [Incident Response - Auth Failure](incident-response.md#1-auth-failure-401-unauthorized).
   - `SchemaViolationError`: See [Incident Response - Schema Mismatch](incident-response.md#3-schema-mismatch-gold-layer).
   - `LockAcquisitionError`: See [Incident Response - Lock Timeout](incident-response.md#4-lock-timeout-lock-expired).
   - `InfrastructureError`: Check local storage and filesystem health.

### Recovery Actions

1. **Fix the Root Cause**:
   - Rotate keys.
   - Update schema.
   - Free up disk space.
1. **Resume Pipeline**:
   - If checkpoint exists:
     ```bash
     bioetl run --pipeline ... --resume
     ```
   - If checkpoint is corrupted (see [Data Recovery](data-recovery.md#scenario-3-lost-checkpoint)):
     ```bash
     bioetl run --pipeline ...
     ```

### Post-Mortem

- Create a P1 Incident Report.
- Analyze why the error wasn't caught by preflight, smoke, or staging-like local verification.
- Add new regression tests if applicable.

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
