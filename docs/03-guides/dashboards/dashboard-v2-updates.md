# Dashboard v2 Updates (Audit 2026-03-28)

Источник истины: `grafana/dashboards/bioetl-*.json`

## Проверенные дашборды

- `bioetl-simple`
- `bioetl-overview-v2`
- `bioetl-dq-v2`
- `bioetl-provider-health-v2`

## Подтверждено по JSON

- Все 4 дашборда используют `refresh: 30s`, `time.from: now-12h`.
- Переменные `simple/overview/dq`: `$pipeline`, `$run_type`.
- Переменные `provider-health-v2`: `$provider`.
- В JSON отсутствуют `$run_id` и `execution`.

## Исправления, внесенные в JSON

1. Удалены устаревшие переменные `run_id` из всех 4 дашбордов.
2. Удалены вводящие в заблуждение формулировки про "Latest Run Only".
3. Исправлен DQ panel `id=12`:

```promql
sum(increase(bioetl_silver_validation_failures_total{table=~"$pipeline"}[24h]))
```

4. Упрощён Provider Health v2:

- removed legacy `Pipeline`/`Execution Timestamp` header section;
- removed duplicate repeated latency gauge `id=103`;
- switched summary counters to 15-minute operational windows;
- kept provider-only filtering because health-check metrics are provider-labeled, not pipeline-labeled.

5. Актуальный repeated latency gauge:

```promql
histogram_quantile(0.95, sum by (le) (rate(bioetl_health_check_latency_seconds_bucket{provider="$provider"}[5m])))
```

6. Добавлен operator drilldown surface:

- `bioetl-overview-v2`, `bioetl-dq-v2`, `bioetl-provider-health-v2` теперь содержат
  dashboard links `Explore Logs (Loki)` и `Explore Traces (Tempo)`;
- `overview.id=1`, `dq.id=1`, `provider.id=1` дублируют этот handoff через data links;
- Loki links используют low-cardinality entrypoint `{job="bioetl"}` и regex filter
  по JSON-полю `pipeline` или `provider`;
- Tempo links сохраняют текущее time range и открывают trace search без попытки
  вводить high-cardinality trace filters.

## Актуальные ключевые панели

- `bioetl-overview-v2`: `id=99`, `id=101`, `id=1..4`, `id=110..115`
- `bioetl-dq-v2`: `id=99`, `id=101`, `id=1..12`, `id=116`
- `bioetl-provider-health-v2`: row `id=91` + панели `1,2,104,7,102`

## Примечание по старым гайдам

Документы в `docs/03-guides/dashboards/`, где фигурируют `$run_id`, `execution` или "latest run only", относятся к устаревшей версии и не описывают текущее состояние JSON.
