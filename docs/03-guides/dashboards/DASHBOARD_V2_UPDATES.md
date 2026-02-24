# Dashboard v2 Updates (Audit 2026-02-24)

Источник истины: `grafana/dashboards/bioetl-*.json`

## Проверенные дашборды

- `bioetl-simple`
- `bioetl-overview-v2`
- `bioetl-dq-v2`
- `bioetl-provider-health-v2`

## Подтверждено по JSON

- Все 4 дашборда используют `refresh: 30s`, `time.from: now-7d`.
- Переменные `simple/overview/dq`: `$pipeline`, `$run_type`.
- Переменные `provider-health-v2`: `$pipeline`, `$provider`.
- В JSON отсутствуют `$run_id` и `execution`.

## Исправления, внесенные в JSON

1. Удалены устаревшие переменные `run_id` из всех 4 дашбордов.
2. Удалены вводящие в заблуждение формулировки про "Latest Run Only".
3. Исправлен DQ panel `id=12`:

```promql
sum(increase(bioetl_silver_validation_failures_total{table=~"$pipeline"}[24h]))
```

4. Исправлен Provider Health panel `id=103`:

```promql
histogram_quantile(0.95, sum by (le) (rate(bioetl_health_check_latency_ms_bucket{provider="$provider"}[5m])))
```

## Актуальные ключевые панели

- `bioetl-overview-v2`: `id=99`, `id=101`, `id=1..4`
- `bioetl-dq-v2`: `id=99`, `id=101`, `id=1..12`
- `bioetl-provider-health-v2`: 2 row-секции (`id=90`, `id=91`) + панели `99,101,1,2,103,7,102`

## Примечание по старым гайдам

Документы в `docs/03-guides/dashboards/`, где фигурируют `$run_id`, `execution` или "latest run only", относятся к устаревшей версии и не описывают текущее состояние JSON.
