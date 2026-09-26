---
trigger: glob
description: "BioETL observability — structured logs, metrics, tracing ports"
globs:
  - "src/**/*.py"
---

# Observability

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

Observability via `LoggerPort`, `MetricsPort`, `TracingPort`, and domain/lifecycle events — not direct structlog/print in domain/application/interfaces.

## Correlation

- `run_id` **MUST** in logs, locks, manifest/ledger, control-plane artifacts
- Formal REQ-OBS "run_id in metrics" = correlation via control plane/logs — **NOT** as Prometheus label
- Label `dataset` (logical table, e.g. `chembl/activity`) **SHOULD** in logs when applicable

## Structured Logging

- Format: structured JSON; retention **30 days**
- Required fields: `timestamp` (UTC), `level`, `run_id`, `pipeline`, `stage`/`phase`
- Recommended: `dataset`, `record_count`
- Application code: `LoggerPort` with keyword context

## Prometheus Guardrails

**Naming:** prefix `bioetl_`, snake_case, unit suffix where applicable. Hyphenated legacy display names are not canonical identifiers.

**MUST NOT** use as metric labels: `run_id`, `manifest_id`, `record_id`, `lineage_fragment_id`, hashes, filesystem paths, raw endpoint IDs.

Per-run correlation: logs, RunManifest, RunLedger, inspection CLI.

Metrics retention: **90 days**.

## Key Metrics (examples)

| Metric | Notes |
| ------ | ----- |
| `bioetl_circuit_breaker_state` | 0=Closed, 1=Half-Open, 2=Open |
| `bioetl_circuit_breaker_trips_total` | Trip counter |
| `bioetl_provider_health_status` | 0=Unhealthy, 1=Degraded, 2=Healthy |
| DQ metrics | e.g. validation score, freshness — bounded labels (`check`, `column`) |

Emit via `MetricsPort`; `NoOpMetrics` / `NoOpTracer` acceptable in Local-Only (Null Object Pattern).

## Required Signals

Lifecycle/stage duration, fetched/Bronze/Silver/Gold/quarantine counts, DQ verdicts, retries, rate limit, circuit state, provider health, writer outcome, checkpoint, lock acquisition/loss, shutdown.

## DQ Anomaly Detection

| Signal | Warning | Critical |
| ------ | ------- | -------- |
| null-rate vs 30-day baseline | >2× | >5× |
| record count vs baseline | <70% | <50% |

Cold start: days 1–7 silence; 8–30 warning-only; day 30+ full alerting.

## Control Plane Artifacts

- **RunManifest**: immutable correlation of config, inputs, fingerprint, outputs, terminal result
- **RunLedger**: append-only stage/history record
- Terminal domain events after state transition; terminal timestamp from captured start anchor + monotonic duration (not nondeterministic wall-clock resample)

## Tracing

- Depend on `TracingPort` facade (OTel-compatible)
- Canonical run correlation attribute; bounded stage/phase attributes
- No direct OTel imports in domain/application
