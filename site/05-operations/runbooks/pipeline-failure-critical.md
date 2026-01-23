# Pipeline Failure: Critical Error (P1)

*Reference: [RULES.md §3.1.1](../../RULES.md#311-классификация-ошибок)*

This runbook describes how to handle critical pipeline failures (P1 incidents).

## Symptoms
- Pipeline crashes with exit code != 0.
- Logs contain `CRITICAL` level messages.
- Alert "Pipeline Failed" fires.
- `errors_total{type="critical"}` metric increments.

## Common Causes
1. **Infrastructure Failure**: Database down, S3 bucket inaccessible, Disk full.
2. **Authentication Failure**: API key expired, invalid credentials.
3. **Schema Violation**: Source data structure changed significantly (Gold layer validation failed).
4. **Lock Acquisition Error**: Unable to acquire lock for `rebuild` or `backfill`.

## Diagnosis Steps
1. **Check Logs**:
   ```bash
   # Filter for CRITICAL errors
   grep "CRITICAL" logs/bioetl.log | jq .
   ```
2. **Identify Error Type**:
   - `AuthFailureError`: See [Incident Response - Auth Failure](incident-response.md#1-auth-failure-401-unauthorized).
   - `SchemaViolationError`: See [Incident Response - Schema Mismatch](incident-response.md#3-schema-mismatch-gold-layer).
   - `LockAcquisitionError`: See [Incident Response - Lock Timeout](incident-response.md#4-lock-timeout-lock-expired).
   - `InfrastructureError`: Check external services (S3, DB).

## Recovery Actions
1. **Fix the Root Cause**:
   - Rotate keys.
   - Update schema.
   - Free up disk space.
2. **Resume Pipeline**:
   - If checkpoint exists:
     ```bash
     make run-pipeline PIPELINE=... ARGS="--resume"
     ```
   - If checkpoint is corrupted (see [Data Recovery](data-recovery.md#scenario-3-lost-checkpoint)):
     ```bash
     make run-pipeline PIPELINE=... ARGS="--ignore-checkpoint"
     ```

## Post-Mortem
- Create a P1 Incident Report.
- Analyze why the error wasn't caught in staging.
- Add new regression tests if applicable.
