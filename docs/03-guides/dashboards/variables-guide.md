______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-03-29**
Источник истины: `grafana/dashboards/*.json`

## Переменные по дашбордам

| Dashboard UID                    | Переменные                                             |
| -------------------------------- | ------------------------------------------------------ |
| `bioetl-overview-v2`             | `$pipeline`, `$run_type`                               |
| `bioetl-control-plane-v1`        | `$pipeline`, `$run_type`                               |
| `bioetl-dq-v2`                   | `$pipeline`, `$run_type`, `$stage`                     |
| `bioetl-runtime`                 | `$pipeline`, `$run_type`, `$stage`                     |
| `bioetl-provider-health-v2`      | `$provider`, `$adapter`                                |
| `bioetl-silver-reject-explorer`  | `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash` |
| `bioetl-workflow-overview`       | `$workflow`, `$status`                                 |

## Определения переменных

| Variable    | Query                                                                                           | Multi | Include All | Refresh                 |
| ----------- | ----------------------------------------------------------------------------------------------- | ----- | ----------- | ----------------------- |
| `$pipeline` | `label_values(bioetl_records_processed_total, pipeline)`                                        | Yes   | Yes         | On dashboard load (`1`) |
| `$run_type` | `label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)`                 | Yes   | Yes         | On dashboard load (`1`) |
| `$stage`    | `label_values(bioetl_records_processed_total{pipeline=~"$pipeline",run_type=~"$run_type"}, stage)` | Yes | Yes | On dashboard load (`1`) |
| `$provider` | `label_values({__name__=~"bioetl_health_check_(success\|degraded\|failures)_total"}, provider)` | Yes   | Yes         | On dashboard load (`1`) |
| `$adapter`  | `label_values(bioetl_circuit_breaker_state, adapter)`                                           | Yes   | Yes         | On dashboard load (`1`) |
| `control_plane.$pipeline` | `label_values(bioetl_control_plane_manifest_writes_total, pipeline)`             | Yes   | Yes         | On dashboard load (`1`) |
| `workflow.$workflow` | `label_values(bioetl_workflow_runs_total, workflow)`                               | Yes   | Yes         | On dashboard load (`1`) |
| `workflow.$status` | `label_values(bioetl_workflow_runs_total, status)`                                   | Yes   | Yes         | On dashboard load (`1`) |
| `explorer.$pipeline` | `label_values(bioetl_records_processed_total, pipeline)` | No | No | On dashboard load (`1`) |
| `explorer.$run_id` | `/ops/quarantine/filter-options?dimension=run_id&pipeline=${pipeline}...` | No | No | On dashboard load (`1`) |
| `explorer.$payload_hash` | textbox | No | No | Manual |

## Важно

- В Prometheus-backed dashboards **нет** переменных `$run_id` и `execution`.
- `bioetl-silver-reject-explorer` остаётся forensic exception:
  `$run_id` и `$payload_hash` используются только в quarantine-backed Explorer,
  а не в Prometheus labels или PromQL.
- В `bioetl-dq-v2` и `bioetl-runtime` дополнительный bounded scope даёт `$stage`.
- В `bioetl-provider-health-v2` используются `$provider` и `$adapter`.
- В `bioetl-workflow-overview` используются только `$workflow` и `$status`.
- Cross-dashboard links должны передавать только target-scoped `var-*`
  параметры; generic `includeVars=true` не считается безопасным handoff.

## Примеры PromQL с переменными

```promql
# Overview/Data Quality/Runtime
sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="bronze"})

# Provider Health p95
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_health_check_latency_seconds_bucket{provider=~"$provider"}[5m])))

# Provider latency panel (ID 102)
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_health_check_latency_seconds_bucket{provider=~"$provider"}[5m])))
```

## Зависимости

- Для `overview/dq/runtime`: `$run_type` зависит от `$pipeline`.
- Для `dq/runtime`: `$stage` зависит от `$pipeline/$run_type` и остаётся bounded
  stage breakdown filter, а не high-cardinality forensic selector.
- Для `control-plane-v1`: `$run_type` зависит от `$pipeline`, но global
  read-panels intentionally не фильтруют underlying metrics по `$pipeline`.
- Для `provider-health-v2`: `$provider` и `$adapter` управляют timeseries и
  summary/gauge панелями; pipeline filter не используется.
- Для `bioetl-workflow-overview`: `$status` и `$workflow` зависят от
  `bioetl_workflow_runs_total`; эти переменные не leaking в non-workflow dashboards.
- Для `bioetl-silver-reject-explorer`: `$pipeline` всегда single-select/no-All.
  Это fail-closed Quarantine Explorer contract; `${pipeline:csv}` здесь не
  допускается.
