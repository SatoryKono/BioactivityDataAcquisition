---
trigger: glob
description: "BioETL error handling — retry, circuit breaker, DQ thresholds"
globs:
  - "src/**/adapters/**"
  - "src/**/http/**"
  - "src/**/*.py"
---

# Error Handling and Resilience

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

## Error Classification

| Type | Behavior | Examples |
| ---- | -------- | -------- |
| Critical | Fail pipeline immediately | Auth failure (401), Gold schema mismatch, DB unavailable |
| Recoverable | Retry within policy | 429, 502/504, transient network |
| Data Quality | Per `invalid_record_policy` | Invalid SMILES, field constraint violation |

Non-retriable auth/validation errors **MUST NOT** retry. Temporary 429/502/504/selected 5xx retry only within policy.

## Retry (Recoverable)

| Parameter | Default |
| --------- | ------- |
| Max attempts | 3 |
| Multiplier | 2.0 (1s, 2s, 4s…) |
| Jitter | 0.1–0.5s SHOULD |

`RetryConfig(deterministic=True)` → jitter via hash, not `random` — must not affect reproducible business output.

## Circuit Breaker

| Parameter | Value |
| --------- | ----- |
| Trigger | 5 consecutive connection/timeout errors |
| Open duration | 5 min (`circuit-breaker.recovery-timeout`) |
| Recovery | Half-Open → 1 probe |
| Alert | Open >10 min |

Metric: `bioetl_circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open).

## DQ Configuration & Thresholds

- Validate DQ config pre-execution: `soft_fail_threshold < hard_fail_threshold`
- Default formal thresholds: **>5%** error rate → warning; **>20%** → fail batch
- Track `record-error-rate` and `entity-error-rate`

## invalid_record_policy

Accepts **only**: `quarantine`, `skip`, `fail`. Generic "always skip DQ errors" invalid without explicit policy.

## DQ Contract System (ADR-045)

| Contract type | Disposition |
| ------------- | ----------- |
| SCHEMA, CONTENT, CONSISTENCY, PROVENANCE | FAIL, WARN, or QUARANTINE |

Policy resolution: exact contract/version → latest version → entity default → global fallback.

DQ **MUST NOT** silently change business values, remove columns, or substitute sentinels. Normalization only as explicit deterministic rule with tests.

## DQ Outcome Observability

Export valid/skipped/quarantined/failed counts, policy, threshold verdict, check/error code, duration to logs and Prometheus (`bioetl_` metrics).

## Provider Health Integration

| Errors | State | Action |
| ------ | ----- | ------ |
| 1–2 consecutive | DEGRADED | adaptive timeout ×2, batch ÷2 |
| ≥3 | UNHEALTHY | pause pipeline, P2 alert |

## Pipeline Failure Semantics

First failed **mandatory** stage → `PipelineRun.FAILED`; subsequent business stages **MUST NOT** execute or mask primary error. Cleanup, terminal observability, lock release in idempotent `finally`.

## Idempotency

Retries, pagination, restart, replay must not duplicate persisted semantic rows. At-least-once transport + deterministic dedup/merge.
