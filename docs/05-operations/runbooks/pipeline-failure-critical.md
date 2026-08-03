______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P0
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-03'

______________________________________________________________________

# Runbook: Critical Pipeline Failure

## Trigger

- ALERT: `PipelineExecutionFailed`
- Severity: Critical (P0)
- Manual report of data ingestion stall or database corruption.

## Impact

- Pipeline stops immediately.
- Potential data loss in Bronze layer if not handled correctly.
- Downstream Gold analytics delayed.

## Preconditions

- Access to logs (Loki/Local).
- Access to checkpoint storage.
- Git repository permissions.

## Procedure

### 1. Diagnosis

1. Identify `run_id` from the logs.
1. Check specific error code (e.g., `AUTHORIZATION_ERROR`, `NETWORK_TIMEOUT`).
1. Verify provider health status.

### 2. Standard Fixes

- **Auth Error**: Update `.env` with fresh credentials.
- **Network Error**: Verify connectivity and retry manually.
- **Schema Error**: Check for provider-side API changes.

### 3. Cleanup & Resume

1. Remove corrupted local files (if any).
1. Resume using `--resume-from <run_id>`.

## Verification

- `bioetl run-manifest show <run_id>` status is `SUCCESS`.
- `uv run python -m scripts.engineering.dev run-tests integration -- -k <provider>`
  for the affected provider slice passes.

## Recovery

- If the resumed run fails again, stop retries and restore the last known good local data/control-plane state before retrying further changes.
- Revert any emergency configuration override or credential rotation that introduced the regression if diagnosis confirms it as the root cause.

## Post-incident

- Log the root cause in the monthly stability report.
- Update circuit breaker settings if necessary.

## Compliance

- Preserve commands executed, affected `run_id`, and evidence paths in the incident record.
- Any cleanup or local-file removal MUST remain consistent with ADR-010 Local-Only handling and with the active recovery runbook set.
