______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-10'

______________________________________________________________________

# SLI / SLO Baseline

## Purpose

This document defines the operational SLI/SLO baseline for the supported
BioETL runtime.

Scope:

- local-only single-instance deployments
- Prometheus-backed shipped metrics and alert rules
- operator-facing reliability targets for pipeline execution, control-plane
  integrity, provider health, and DQ freshness

This baseline is an internal operations target, not an external customer SLA.

## Principles

- Use low-cardinality Prometheus signals only.
- Keep run-level and record-level investigation in logs, traces, quarantine
  explorer, and run-manifest artifacts.
- Reuse shipped alert rules where possible so SLO drift is actionable.
- Treat `shutdown` as a controlled terminal outcome, not a hard pipeline
  failure, unless an incident review decides otherwise.

## Canonical SLI Set

| SLI                               | Metric source                                                                                                   | Window                  | Target baseline                                                                  | Alert / runbook linkage                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Pipeline terminal success rate    | \`bioetl_pipeline_runs_total{status=~"success                                                                   | failed"}\`              | 7d rolling                                                                       | `>= 95%` success per `pipeline,run_type`                                                                            |
| Control-plane write success ratio | `bioetl_control_plane_manifest_writes_total`, `bioetl_control_plane_ledger_appends_total`                       | 7d rolling              | `>= 99%` successful writes per `pipeline`                                        | `BioETLControlPlaneManifestWriteFailed`, `BioETLRunLedgerAppendFailed` -> `runbooks/run-manifest-inspection.md`     |
| Control-plane read success ratio  | `bioetl_control_plane_reads_total`                                                                              | 24h rolling             | `>= 99%` successful reads per `store,operation`                                  | `BioETLControlPlaneReadFailureRate` -> `runbooks/observability-checklist.md`                                        |
| Provider health completion ratio  | `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`, `bioetl_health_check_failures_total` | 24h rolling             | `>= 95%` successful or degraded completions per `provider`                       | `BioETLProviderHealthCheckFailuresDetected`, `BioETLProviderFailureRateHigh` -> `runbooks/incident-response.md`     |
| Retry exhaustion containment      | `bioetl_data_source_retry_exhausted_total`                                                                      | 1h rolling              | `< 3` exhaustions per `provider,operation`                                       | `BioETLProviderRetriesExhausted`, `BioETLProviderRetriesExhaustedPersistent` -> `runbooks/incident-response.md`     |
| DQ quarantine ratio               | `bioetl_dq_records_quarantined_total` vs `bioetl_records_processed_total{stage="bronze"}`                       | 24h rolling             | `<= 5%` per `pipeline,run_type` when `bronze >= 20`                              | `BioETLDQQuarantineRateHigh`, `BioETLDQQuarantineRateCritical` -> `runbooks/dq-failure-investigation.md`            |
| DQ validation health              | `bioetl_dq_validation_failures_total`, `bioetl_dq_anomaly_detected`, `bioetl_dq_validation_score`               | 24h rolling             | no hard-fail validation failures; investigate any critical anomalies immediately | `BioETLDQValidationFailuresCritical`, `BioETLDQCriticalAnomaliesDetected` -> `runbooks/dq-failure-investigation.md` |
| Data freshness lag                | `bioetl_data_freshness_seconds`                                                                                 | continuous / 24h review | `<= 24h` lag for active pipelines; `> 72h` is critical                           | `BioETLDataFreshnessLagHigh`, `BioETLDataFreshnessLagCritical` -> `runbooks/dq-failure-investigation.md`            |

## PromQL Reference

### Pipeline terminal success rate

```promql
sum by (pipeline, run_type) (
  increase(bioetl_pipeline_runs_total{status="success"}[7d])
)
/
clamp_min(
  sum by (pipeline, run_type) (
    increase(bioetl_pipeline_runs_total{status=~"success|failed"}[7d])
  ),
  1
)
```

### Control-plane write success ratio

```promql
1 -
(
  sum by (pipeline, run_type) (
    increase(bioetl_control_plane_manifest_writes_total{status="failed"}[7d])
  )
  /
  clamp_min(
    sum by (pipeline, run_type) (
      increase(bioetl_control_plane_manifest_writes_total[7d])
    ),
    1
  )
)
```

Apply the same pattern to `bioetl_control_plane_ledger_appends_total`.

### Control-plane read success ratio

```promql
1 -
(
  sum by (store, operation) (
    increase(bioetl_control_plane_reads_total{status="failed"}[24h])
  )
  /
  clamp_min(
    sum by (store, operation) (
      increase(bioetl_control_plane_reads_total[24h])
    ),
    1
  )
)
```

### Provider health completion ratio

```promql
(
  sum by (provider) (increase(bioetl_health_check_success_total[24h]))
  +
  sum by (provider) (increase(bioetl_health_check_degraded_total[24h]))
)
/
clamp_min(
  sum by (provider) (
    increase(bioetl_health_check_success_total[24h])
    + increase(bioetl_health_check_degraded_total[24h])
    + increase(bioetl_health_check_failures_total[24h])
  ),
  1
)
```

### DQ quarantine ratio

```promql
sum by (pipeline, run_type) (
  increase(bioetl_dq_records_quarantined_total[24h])
)
/
clamp_min(
  sum by (pipeline, run_type) (
    increase(bioetl_records_processed_total{stage="bronze"}[24h])
  ),
  1
)
```

### Data freshness lag

```promql
clamp_min(time() - max by (pipeline, entity) (bioetl_data_freshness_seconds), 0)
```

Current implementation note: `bioetl_data_freshness_seconds` is written from
the canonical ingestion anchor carried into postrun/DQ evaluation for the run
(currently `PipelineContext.started_at`, which is also propagated as the record
`_ingestion_ts` default across runtime writes). The resulting lag reflects
runtime age from that ingestion anchor rather than a wall-clock freshness
publication timestamp. Treat this metric as *run recency / ingestion-anchor lag*,
not as authoritative source-publication freshness.

That same canonical ingestion anchor is also the timestamp source for DQ
anomaly evaluation and DQ baseline updates. When anomaly records or baseline
decisions are inspected, their timing should be interpreted as anchored to the
run freshness timestamp rather than to an infrastructure-local monitor clock.

## Interpretation Rules

- If an alert threshold is stricter than the SLO review target, follow the
  alert first and the SLO review second.
- If the denominator is `< 20` bronze records or no relevant runs exist in the
  window, treat the SLI as informational rather than enforceable.
- `degraded` provider health counts as completed but not fully healthy. Repeated
  degraded states still require investigation if they persist.
- If `bioetl_dq_monitor_disabled_total` increments for an active pipeline, treat
  anomaly-based DQ signals as degraded coverage until the DQ monitor is restored.
- Freshness SLI/SLO review currently tracks the age of the latest successful
  run ingestion anchor. For exact source-ingestion chronology beyond the
  current run boundary, use manifests, lineage, and audit artifacts together
  with the gauge value. Grafana/alert interpretations of
  `bioetl_data_freshness_seconds` must preserve this semantics and must not
  relabel it as source-publication freshness without an additional metric.
- For local-only stacks, temporary tracing disablement or maintenance windows
  should be annotated in the incident log rather than silently ignored.

## Review Cadence

- Review these baselines whenever shipped Prometheus rules or dashboard
  semantics change.
- Revalidate after changes to:
  - `docs/04-reference/contracts/observability.md`
  - `grafana/prometheus-rules/bioetl_observability.yml`
  - `src/bioetl/infrastructure/observability/_metrics_defs_*.py`
- Minimum review cadence: once per release wave that changes observability
  contracts or operator workflows.

## Related References

- [Monitoring Guide](01-monitoring-guide.md)
- [Observability Checklist](runbooks/observability-checklist.md)
- [Observability Contract](../04-reference/contracts/observability.md)
- [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md)
