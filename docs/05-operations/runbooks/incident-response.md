# Incident Response Playbook

This document outlines the standard operating procedures for responding to production incidents in the BioETL platform.

## Severity Levels

| Level | Description | Response SLA | Recovery SLA |
|-------|-------------|--------------|--------------|
| **P0** | System unavailable or critical data loss (e.g., S3 bucket deleted, DB down). | 15 min | 1 hour |
| **P1** | Critical pipeline failure (Core Data: ChEMBL, PubChem). | 1 hour | 4 hours |
| **P2** | Secondary pipeline failure (e.g., enrichment sources). | 8 hours | 24 hours |
| **P3** | Warning / Data Quality anomalies / Non-blocking bugs. | 24 hours | Next Sprint |

## Common Alerts & Actions

### 1. Auth Failure (`401 Unauthorized`)
*   **Symptom**: Logs show repeated `401` errors from a provider API.
*   **Severity**: P1 (if blocking) or P2.
*   **Diagnosis**: API key has expired or is invalid.
*   **Action**:
    1.  Verify the key in the secrets manager (or `.env` for local).
    2.  Rotate the key: Generate a new one from the provider's portal.
    3.  Update the environment variable `BIOETL_{PROVIDER}_API_KEY`.
    4.  Restart the pipeline.

### 2. Rate Limit Exhausted (`429 Too Many Requests`)
*   **Symptom**: Spike in `errors_total{type="recoverable"}` metric. Pipeline slows down effectively to a halt.
*   **Severity**: P2.
*   **Diagnosis**: The configured `requests_per_second` exceeds the provider's current allowance.
*   **Action**:
    1.  Check the provider's status page for global issues.
    2.  Reduce the rate limit in the pipeline config (`configs/pipelines/{name}.yaml`):
        ```yaml
        rate_limit:
          requests_per_second: 2  # Decrease from 5
        ```
    3.  Redeploy/Restart the pipeline.

### 3. Schema Mismatch (Gold Layer)
*   **Symptom**: Pipeline fails with `schema_violations > 0` and `SchemaValidationError`.
*   **Severity**: P1.
*   **Diagnosis**: The source API has changed its response format (Schema Drift), breaking the Gold contract.
*   **Action**:
    1.  Inspect the raw data in Bronze to identify the new field or type change.
    2.  **Short-term**: If the field is non-critical, mark it as optional in the Pydantic model to unblock the pipeline.
    3.  **Long-term**: Update the Gold schema and Pydantic models to reflect the change (requires a PR and release).

### 4. Lock Timeout ("Lock expired")
*   **Symptom**: Alert "Lock expired" fires, or pipeline refuses to start.
*   **Severity**: P2.
*   **Diagnosis**: A previous worker crashed without releasing the Redis lock, or a job ran longer than the 4-hour hard limit.
*   **Action**:
    1.  Check for "zombie" processes on the worker nodes.
    2.  Manually release the lock:
        ```bash
        make release-lock PIPELINE=chembl_activity
        ```
    3.  Investigate why the job took so long (performance regression?).

## Escalation Policy

If an incident cannot be resolved within the Response SLA:
1.  **On-Call Engineer**: Post status update in `#bioetl-alerts`.
2.  **Tech Lead**: Notify stakeholders if P0/P1.
3.  **Post-Mortem**: Required for all P0/P1 incidents within 48 hours.
