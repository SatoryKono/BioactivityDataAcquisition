# Variables Guide (Grafana Dashboards)

Дата сверки: **2026-02-24**  
Источник истины: `grafana/dashboards/*.json`

## Переменные по дашбордам

| Dashboard UID | Переменные |
|---|---|
| `bioetl-simple` | `$pipeline`, `$run-type` |
| `bioetl-overview-v2` | `$pipeline`, `$run-type` |
| `bioetl-dq-v2` | `$pipeline`, `$run-type` |
| `bioetl-provider-health-v2` | `$pipeline`, `$provider` |

## Определения переменных

| Variable | Query | Multi | Include All | Refresh |
|---|---|---|---|---|
| `$pipeline` | `label-values(bioetl-records-processed-total, pipeline)` | Yes | Yes | On dashboard load (`1`) |
| `$run-type` | `label-values(bioetl-records-processed-total{pipeline=~"$pipeline"}, run-type)` | Yes | Yes | On dashboard load (`1`) |
| `$provider` | `label-values(bioetl-health_check-latency-ms-bucket, provider)` | Yes | Yes | On dashboard load (`1`) |

## Важно

- В актуальных JSON **нет** переменных `$run-id` и `execution`.
- В `bioetl-provider-health-v2` используется и `$pipeline`, и `$provider`.

## Примеры PromQL с переменными

```promql
# DQ/Overview/Simple
sum(bioetl-records-processed-total{pipeline=~"$pipeline", run-type=~"$run-type", stage="bronze"})

# Provider Health p95
histogram-quantile(0.95, sum by (le, provider) (rate(bioetl-health_check-latency-ms-bucket{provider=~"$provider"}[5m])))

# Provider repeat panel (ID 103)
histogram-quantile(0.95, sum by (le) (rate(bioetl-health_check-latency-ms-bucket{provider="$provider"}[5m])))
```

## Зависимости

- Для `simple/overview/dq`: `$run-type` зависит от `$pipeline`.
- Для `provider-health-v2`: `$provider` независим от `$pipeline`, но обе переменные участвуют в фильтрации панелей.

