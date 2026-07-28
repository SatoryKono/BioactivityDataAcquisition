______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-03-30'

______________________________________________________________________

# Incident Response Playbook

## Trigger

- Run this procedure when an operational alert requires triage, stabilization, and incident coordination.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### UI entry (Dashboard System 2.0)

1. **Fleet / Overview** (`bioetl-overview-v2`) or **Incident Workspace**
   (`bioetl-incident-v1`) for alert/first-suspect hops.
2. Domain explorers: Pipeline (`bioetl-runtime`), Provider
   (`bioetl-provider-health-v2`), Data Trust (`bioetl-dq-v2`), Trust
   (`bioetl-control-plane-v1`).
3. **Run Explorer** (`bioetl-run-explorer-v1`) for exact HTTP identity / processed
   records (`run_id` never a Prometheus label).

### Severity Levels

| Level  | Description                                                                             | Response SLA | Recovery SLA |
| ------ | --------------------------------------------------------------------------------------- | ------------ | ------------ |
| **P0** | System unavailable or critical data loss (e.g., local storage corrupted, disk failure). | 15 min       | 1 hour       |
| **P1** | Critical pipeline failure (Core Data: ChEMBL, PubChem).                                 | 1 hour       | 4 hours      |
| **P2** | Secondary pipeline failure (e.g., enrichment sources).                                  | 8 hours      | 24 hours     |
| **P3** | Warning / Data Quality anomalies / Non-blocking bugs.                                   | 24 hours     | Next Sprint  |

### Common Alerts & Actions

### 1. Auth Failure (`401 Unauthorized`)

- **Symptom**: Logs show repeated `401` errors from a provider API.
- **Severity**: P1 (if blocking) or P2.
- **Diagnosis**: API key has expired or is invalid.
- **Action**:
  1. Verify the key in the secrets manager (or `.env` for local).
  1. Rotate the key: Generate a new one from the provider's portal.
  1. Update the environment variable `BIOETL_{PROVIDER}_{KEY}` (for example: `BIOETL_UNIPROT_API_KEY`).
  1. Restart the pipeline.

### 2. Rate Limit Exhausted (`429 Too Many Requests`)

- **Symptom**: Spike in `errors-total{type="recoverable"}` metric. Pipeline slows down effectively to a halt.
- **Severity**: P2.
- **Diagnosis**: The configured `requests-per-second` exceeds the provider's current allowance.
- **Action**:
  1. Check the provider's status page for global issues.
  1. Reduce the rate limit in the pipeline config (`configs/entities/{provider}/{entity}.yaml`):
     ```yaml
     rate-limit:
       requests-per-second: 2  # Decrease from 5
     ```
  1. Redeploy/Restart the pipeline.

### 3. Schema Mismatch (Gold Layer)

- **Symptom**: Pipeline fails with `schema-violations > 0` and `SchemaValidationError`.
- **Severity**: P1.
- **Diagnosis**: The source API has changed its response format (Schema Drift), breaking the Gold contract.
- **Action**:
  1. Inspect the raw data in Bronze to identify the new field or type change.
  1. **Short-term**: If the field is non-critical, mark it as optional in the Pydantic model to unblock the pipeline.
  1. **Long-term**: Update the Gold schema and Pydantic models to reflect the change (requires a PR and release).

### 4. Lock Timeout ("Lock expired")

- **Symptom**: Alert "Lock expired" fires, or pipeline refuses to start.
- **Severity**: P2.
- **Diagnosis**: A previous local process crashed without releasing `MemoryLock`, or a job ran longer than the 4-hour hard limit.
- **Action**:
  1. Check for stuck local Python processes running this pipeline.
  1. Identify the lock owner `run-id` from logs (or from the failed run context).
  1. Manually release the lock:
     ```bash
     bioetl lock release --pipeline chembl_activity --run-id <RUN_ID>
     ```
  1. Investigate why the job took so long (performance regression?).



### 5. CI Policy Gate: Deprecated GitHub Actions Runtime

- **Symptom**: GitHub Actions jobs fail with `Node.js 20 actions are deprecated` and `Process completed with exit code 1`.
- **Severity**: P1 for blocking protected branches; P2 otherwise.
- **Diagnosis**: Workflow/composite action references use non-vetted or non-pinned `actions/*` runtime versions.
- **Action**:
  1. Run repository policy gate locally:
     ```bash
     uv run python -m scripts.engineering.repo check-actions-runtime-policy
     ```
  2. Replace failing references with vetted pinned SHAs from CI runtime policy (see `scripts/engineering/repo/check_github_actions_runtime_policy.py`).
  3. Re-run affected workflow(s) and verify no Node-runtime policy annotations remain.
  4. If policy or SHAs must rotate, update checker allowlist and triage notes in `docs/05-operations/verification/ci-failure-triage-2026-05-05.md`.

### Escalation Policy

- If an incident cannot be resolved within the Response SLA:

1. **On-Call Engineer**: Post status update in `#bioetl-alerts`.
1. **Tech Lead**: Notify stakeholders if P0/P1.
1. **Post-Mortem**: Required for all P0/P1 incidents within 48 hours.

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
