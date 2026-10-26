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

| Alert Name | Defining Rule File | Procedure / Anchor |
| --- | --- | --- |
| `BioETLProviderHttpErrorRateHigh` | `bioetl_observability.yml` | [1. Provider HTTP Error Rate High](#1-provider-http-error-rate-high) |
| `BioETLProviderRateLimiterTokensDepleted` | `bioetl_observability.yml` | [2. Provider Rate Limiter Exhausted](#2-provider-rate-limiter-exhausted) |
| `BioETLProviderRateLimiterWaitHigh` | `bioetl_observability.yml` | [2. Provider Rate Limiter Exhausted](#2-provider-rate-limiter-exhausted) |
| `BioETLGoldValidationFailuresCritical` | `bioetl_observability.yml` | [3. Schema Mismatch (Gold Layer)](#3-schema-mismatch-gold-layer) |
| `BioETLProviderHealthCheckFailuresDetected` | `bioetl_observability.yml` | [6. Provider Failures / Health Checks](#6-provider-failures--health-checks) |
| `BioETLProviderFailureRateHigh` | `bioetl_observability.yml` | [6. Provider Failures / Health Checks](#6-provider-failures--health-checks) |
| `BioETLProviderRetriesExhausted` | `bioetl_observability.yml` | [7. Provider Retries / Circuit Breaker](#7-provider-retries--circuit-breaker) |
| `BioETLProviderRetriesExhaustedPersistent` | `bioetl_observability.yml` | [7. Provider Retries / Circuit Breaker](#7-provider-retries--circuit-breaker) |
| `BioETLCircuitBreakerStuckOpen` | `bioetl_observability.yml` | [7. Provider Retries / Circuit Breaker](#7-provider-retries--circuit-breaker) |
| `BioETLProviderAdapterLatencyHigh` | `bioetl_observability.yml` | [8. Provider Latency](#8-provider-latency) |

### 1. Provider HTTP Error Rate High

- **Alert**: `BioETLProviderHttpErrorRateHigh`
- **Symptom**: Logs show repeated `401 Unauthorized` errors or other HTTP errors from a provider API.
- **Severity**: P1 (if blocking) or P2.
- **Diagnosis**: Determine specific HTTP status from logs (e.g. 401 for auth failure, 5xx for provider outage, 429 for provider quota exhaustion) before attempting mitigation.
- **Action**:
  1. Check logs to establish the exact error type and status code.
  1. If 401: Verify and rotate the key in secrets manager/`BIOETL_{PROVIDER}_{KEY}`, then restart pipeline.
  1. For 5xx: Check provider status page and await resolution.

### 2. Provider Rate Limiter Exhausted

- **Alert**: `BioETLProviderRateLimiterTokensDepleted` / `BioETLProviderRateLimiterWaitHigh`
- **Symptom**: Internal rate limiter is throttling requests to provider, causing high wait times or token depletion.
- **Severity**: P2.
- **Diagnosis**: The pipeline's internal rate limiting configuration is restricting throughput, preventing a real 429 from the provider but slowing down ingestion.
- **Action**:
  1. Check the provider's status page for global issues.
  1. Review provider documentation for allowed quotas. Do not blindly reduce rate limits unless a real 429 is observed or quotas changed.
     (`configs/providers/{provider}.yaml`), not entity YAML:
     ```yaml
     source:
       rate_limit:
         requests_per_second: 2  # Decrease from the current value
     ```
  1. Redeploy/Restart the pipeline.

### 3. Schema Mismatch (Gold Layer)

- **Alert**: `BioETLGoldValidationFailuresCritical`
- **Symptom**: Pipeline fails with `schema-violations > 0` and `SchemaValidationError`.
- **Severity**: P1.
- **Diagnosis**: Gold validation failed. This may indicate Schema Drift, upstream bugs, or data anomalies. It does not strictly guarantee schema drift.
- **Action**:
  1. See [pipeline-failure-dq.md](pipeline-failure-dq.md) for the correct resolution procedure.

### 4. Lock Timeout

- **Alert**: None (Manual observation / Pipeline refuses to start)
- **Symptom**: Logs show "Lock expired", or pipeline refuses to start.
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


### 6. Provider Failures / Health Checks

- **Alert**: `BioETLProviderHealthCheckFailuresDetected` / `BioETLProviderFailureRateHigh`
- **Symptom**: Provider health checks are failing or failure rate exceeds threshold.
- **Severity**: P1 (if blocking) or P2.
- **Diagnosis**: The provider endpoint is unresponsive or returning excessive failures.
- **Action**: Check provider status page. Review adapter logs.

### 7. Provider Retries / Circuit Breaker

- **Alert**: `BioETLProviderRetriesExhausted` / `BioETLProviderRetriesExhaustedPersistent` / `BioETLCircuitBreakerStuckOpen`
- **Symptom**: Retries for a provider have been exhausted, or circuit breaker is stuck open.
- **Severity**: P2.
- **Diagnosis**: `RetriesExhausted` indicates a failure to process a payload after all attempts. `CircuitBreakerStuckOpen` indicates a protective state where requests are being rejected fast to protect the upstream.
- **Action**: Verify if the provider is down. Temporarily disable the pipeline if there is an extended outage.

### 8. Provider Latency

- **Alert**: `BioETLProviderAdapterLatencyHigh`
- **Symptom**: High latency observed in adapter requests to the provider.
- **Severity**: P3.
- **Diagnosis**: The provider API is responding slower than usual. This may or may not correlate with active pipeline backlogs.
- **Action**: Check network health and provider status. Consider reducing concurrency if the provider is struggling.

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
