# Pipeline Failure: Critical Error (P1)

*Reference: [RULES.md §3.1.1](../../00-project/RULES.md#311-классификация-ошибок)*

This runbook describes how to handle critical pipeline failures (P1 incidents).

## Symptoms

- Pipeline crashes with exit code != 0.
- Logs contain `CRITICAL` level messages.
- Alert "Pipeline Failed" fires.
- `errors-total{type="critical"}` metric increments.

## Common Causes

1. **Infrastructure Failure**: Local storage unavailable, disk full, filesystem errors.
1. **Authentication Failure**: API key expired, invalid credentials.
1. **Schema Violation**: Source data structure changed significantly (Gold layer validation failed).
1. **Lock Acquisition Error**: Unable to acquire lock for `rebuild` or `backfill`.

## Diagnosis Steps

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

## Recovery Actions

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

## Post-Mortem

- Create a P1 Incident Report.
- Analyze why the error wasn't caught in staging.
- Add new regression tests if applicable.
