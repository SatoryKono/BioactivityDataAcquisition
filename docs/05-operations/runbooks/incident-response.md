______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-10-15'

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

### Alert Mapping Table

Exact identifiers come from [the Prometheus rules](../../../grafana/prometheus-rules/bioetl_observability.yml).
All nine alerts whose `runbook` annotation points here have a procedure below.
The Gold row links to its canonical DQ runbook; it does not change that annotation.
Symptoms and log messages are not alert identifiers.

| Exact alertname | Signal | Procedure |
| --- | --- | --- |
| `BioETLProviderFailureRateHigh` | Health-check failure ratio | [Provider health](#6-provider-health-and-latency) |
| `BioETLProviderHealthCheckFailuresDetected` | Failed health checks | [Provider health](#6-provider-health-and-latency) |
| `BioETLProviderAdapterLatencyHigh` | Adapter latency | [Provider latency](#6-provider-health-and-latency) |
| `BioETLProviderHttpErrorRateHigh` | HTTP error ratio | [HTTP errors](#1-provider-http-errors) |
| `BioETLProviderRateLimiterWaitHigh` | Internal limiter wait | [Rate limiter](#2-internal-rate-limiter-pressure) |
| `BioETLProviderRateLimiterTokensDepleted` | Internal token availability | [Rate limiter](#2-internal-rate-limiter-pressure) |
| `BioETLProviderRetriesExhausted` | One or two exhaustion events in one hour | [Retry exhaustion](#7-retry-exhaustion) |
| `BioETLProviderRetriesExhaustedPersistent` | At least three exhaustion events in one hour | [Retry exhaustion](#7-retry-exhaustion) |
| `BioETLCircuitBreakerStuckOpen` | Circuit-breaker state | [Circuit breaker](#8-circuit-breaker-stuck-open) |
| `BioETLGoldValidationFailuresCritical` | Gold hard-fail validation | [DQ runbook](pipeline-failure-dq.md) and [local triage](#3-schema-mismatch-gold-layer) |

### 1. Provider HTTP Errors

- **Alert**: `BioETLProviderHttpErrorRateHigh`.
- **Symptom**: Elevated HTTP errors. Inspect actual status codes: `401 Unauthorized`
  is one possible symptom, not what this aggregate alert proves.
- **Severity**: P1 (if blocking) or P2.
- **Diagnosis**: For confirmed 401/403 responses, inspect credentials and permissions.
  For 429 or 5xx responses, inspect provider limits, availability, and retry logs
  before changing credentials. Never include secret values in incident evidence.
- **Action**:
  1. Verify the key in the secrets manager (or `.env` for local).
  1. Rotate the key only if invalid or expired credentials are confirmed.
  1. Update the environment variable `BIOETL_{PROVIDER}_{KEY}` (for example: `BIOETL_UNIPROT_API_KEY`).
  1. Restart the pipeline.

### 2. Internal Rate-Limiter Pressure

- **Alerts**: `BioETLProviderRateLimiterWaitHigh` and `BioETLProviderRateLimiterTokensDepleted`.
- **Symptom**: Elevated internal limiter wait or depleted tokens; neither alone
  proves a provider returned HTTP 429. Check response logs separately.
- **Severity**: P2.
- **Diagnosis**: Compare local concurrency, configured rate, and the provider's
  documented allowance. A local limiter signal is not evidence of an HTTP status.
- **Action**:
  1. Check the provider's status page for global issues.
  1. Reduce the rate limit in the **provider** config
     (`configs/providers/{provider}.yaml`), not entity YAML:
     ```yaml
     source:
       rate_limit:
         requests_per_second: 2  # Decrease from the current value
     ```
  1. Redeploy/Restart the pipeline.

### 3. Schema Mismatch (Gold Layer)

- **Alert**: `BioETLGoldValidationFailuresCritical`; follow the canonical
  [Pipeline Failure — Data Quality](pipeline-failure-dq.md) procedure.
- **Symptom**: Pipeline fails with `schema-violations > 0` and `SchemaValidationError`.
- **Severity**: P1.
- **Diagnosis**: A Gold hard-fail does not prove upstream schema drift. Inspect the
  exact rule, field/type, transformation, and raw record to distinguish malformed
  data, contract violations, and actual schema changes.
- **Action**:
  1. Inspect the raw data in Bronze to identify the new field or type change.
  1. Preserve the failed run and follow the DQ runbook; do not weaken nullability,
     schema checks, or quarantine rules merely to make the run pass.
  1. Change a contract only after evidence and review establish the intended
     schema (requires a PR and release).

### 4. Lock Timeout

- **Symptom**: Logs report "Lock expired", or a pipeline refuses to start.
  This is a log symptom, not an alertname. Checkpoint alerts describe checkpoint
  operations and are not lock-expiry detectors.
- **Severity**: P2.
- **Diagnosis**: A previous local process crashed without releasing `MemoryLock`, or a job ran longer than the 4-hour hard limit.
- **Action**:
  1. Check for stuck local Python processes running this pipeline.
  1. Identify the lock owner `run-id` from logs (or from the failed run context).
  1. Follow [Stale Lock](stale-lock.md): if a worker is still alive, do **not**
     steal the lock; stop the duplicate or wait. If the holder is dead, kill
     any zombie process and start a new `bioetl run`. `bioetl lock release` only
     affects the **current process** MemoryLock (ADR-010); it is not
     cross-process crash recovery and it is not Redis.



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

### 6. Provider Health and Latency

- **Alerts**: `BioETLProviderFailureRateHigh`,
  `BioETLProviderHealthCheckFailuresDetected`, and `BioETLProviderAdapterLatencyHigh`.
- **Diagnosis**: Identify the provider and window; inspect probe failures or
  request latency respectively. Neither signal alone identifies an auth fault.
- **Action**: Check provider status, network reachability, request logs, and local
  load. Compare failed and successful requests. Preserve evidence and escalate
  before changing credentials or request limits.

### 7. Retry Exhaustion

- **Alerts**: `BioETLProviderRetriesExhausted` and `BioETLProviderRetriesExhaustedPersistent`.
- **Diagnosis**: Inspect events by provider and operation. The rules distinguish
  one or two exhaustion events from at least three in one hour; this is not the
  same signal as circuit-breaker state.
- **Action**: Preserve the final error and retry history, distinguish transient
  from permanent failures, and check provider availability. Do not add unbounded
  retries. Escalate persistent failures with the affected operation.

### 8. Circuit Breaker Stuck Open

- **Alert**: `BioETLCircuitBreakerStuckOpen`.
- **Diagnosis**: Inspect adapter state and transition logs. The rule uses a
  rolling maximum; firing does not prove every instant in the window was open
  or that retry exhaustion caused the state.
- **Action**: Diagnose the provider/network fault and verify recovery before
  resuming traffic. Do not disable the breaker or force repeated requests against
  a failing provider merely to clear the alert.

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
