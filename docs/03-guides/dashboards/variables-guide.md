# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-03-29**  
Источник истины: `grafana/dashboards/*.json`

## Переменные по дашбордам

| Dashboard UID | Переменные |
|---|---|
| `bioetl-overview-v2` | `$pipeline`, `$run_type` |
| `bioetl-dq-v2` | `$pipeline`, `$run_type` |
| `bioetl-runtime` | `$pipeline`, `$run_type` |
| `bioetl-provider-health-v2` | `$provider` |

## Определения переменных

| Variable | Query | Multi | Include All | Refresh |
|---|---|---|---|---|
| `$pipeline` | `label_values(bioetl_records_processed_total, pipeline)` | Yes | Yes | On dashboard load (`1`) |
| `$run_type` | `label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)` | Yes | Yes | On dashboard load (`1`) |
| `$provider` | `label_values(bioetl_provider_health_status, provider)` | Yes | Yes | On dashboard load (`1`) |

## Важно

- В актуальных JSON **нет** переменных `$run_id` и `execution`.
- В `bioetl-provider-health-v2` используется только `$provider`.

## Примеры PromQL с переменными

```promql
# Overview/Data Quality/Runtime
sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="bronze"})

# Provider Health p95
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_health_check_latency_seconds_bucket{provider=~"$provider"}[5m])))

# Provider repeat panel (ID 102)
histogram_quantile(0.95, sum by (le) (rate(bioetl_health_check_latency_seconds_bucket{provider="$provider"}[5m])))
```

## Зависимости

- Для `overview/dq/runtime`: `$run_type` зависит от `$pipeline`.
- Для `runtime`: `$run_type` зависит от `$pipeline`; Loki panels используют `$pipeline`, а alert-condition panels используют оба фильтра.
- Для `provider-health-v2`: `$provider` управляет и timeseries, и summary/gauge панелями; pipeline filter не используется.
