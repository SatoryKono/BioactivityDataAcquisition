# BioETL Dashboards v2: Usage

Дата сверки: **2026-03-28**  
Источник истины: `grafana/dashboards/*.json`

## Какие дашборды использовать

| Dashboard | UID | Для чего |
|---|---|---|
| Data Quality v2 | `bioetl-dq-v2` | Качество данных, карантин, аномалии, freshness |
| Overview v2 | `bioetl-overview-v2` | Общее состояние пайплайна, control-plane и lineage health |
| Runtime | `bioetl-runtime` | Runtime triage: warnings, unstructured logs, alert conditions |
| Provider Health v2 | `bioetl-provider-health-v2` | Latency/успехи health_check провайдеров |

## Фильтрация

- `bioetl-overview-v2`, `bioetl-dq-v2`, `bioetl-runtime`: `$pipeline`, `$run_type`
- `bioetl-runtime`: `$pipeline`, `$run_type`
- `bioetl-provider-health-v2`: `$provider`
- Переменные `$run_id` и `execution` не используются.

## Что смотреть в первую очередь

1. `bioetl-overview-v2`, panel `id=4`:
`sum(gold) / clamp_min(sum(bronze), 1)`
2. `bioetl-dq-v2`, panel `id=2`:
`(gold + quarantined) / clamp_min(bronze, 1)`
3. `bioetl-dq-v2`, panel `id=6`, `id=7`, `id=12`:
рост quarantine/threshold/failures за 24h.
4. `bioetl-provider-health-v2`, panel `id=1`, `id=104`, `id=2`, `id=7`, `id=102`:
p95 latency, failure-rate и 15-минутный объём health checks по провайдерам.
5. `bioetl-runtime`, panel `id=2`, `id=3`, `id=4`, `id=5`, `id=6`, `id=7`:
warnings, unstructured logs и alert-condition сигналы по DQ/control-plane/provider/freshness.
6. `bioetl-overview-v2`, panel `id=111`, `id=112`, `id=113`, `id=114`, `id=115`:
manifest/ledger failures, checkpoint incompatibilities, missing lineage refs и fragment outcomes по `layer/status`.

## Drilldown

- `bioetl-overview-v2`: dashboard links `Explore Logs (Loki)` и `Explore Traces (Tempo)` открывают Grafana Explore в текущем time range. Panel `id=1` (`Processing Pipeline`) дублирует этот handoff через data links.
- `bioetl-dq-v2`: dashboard links `Explore Logs (Loki)` и `Explore Traces (Tempo)` плюс panel `id=1` (`Data Flow: Bronze -> Silver -> Gold`) дают тот же переход для DQ incidents и freshness investigation.
- `bioetl-provider-health-v2`: dashboard links `Explore Logs (Loki)` и `Explore Traces (Tempo)` плюс panel `id=1` (`Health Check Latency by Provider (p95)`) дают быстрый переход из provider health surface в correlation flow.
- `bioetl-runtime`: dashboard links `Explore Logs (Loki)` и `Explore Traces (Tempo)` плюс panel `id=9` (`Log Hygiene Trend (5m)`) дают короткий путь из warning/unstructured-log spikes в Explore.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.

## Важные пороги (из JSON)

- `simple.id=4`: red `<0.8`, orange `>=0.8`, green `>=0.95`
- `overview.id=4`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=5`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=8`: yellow `>=3600s`, red `>=21600s`
- `overview.id=111`: yellow `>=1`, red `>=5`
- `overview.id=112`: yellow `>=1`, red `>=5`
- `overview.id=113`: yellow `>=1`, red `>=5`
- `overview.id=114`: yellow `>=1`, red `>=10`
- `provider.id=104`: yellow `>=5%`, red `>=20%`
- `provider.id=102`: yellow `>=0.5s`, orange `>=2s`, red `>=5s`

## Частые проблемы

1. `No data`:
проверьте `http://localhost:8000/metrics`, затем `http://localhost:9090/targets`.
2. Пустой `$provider`:
нет серии `bioetl_health_check_success_total` в metrics endpoint.
3. Пустой `$run_type`:
нет метрик `bioetl_records_processed_total` для выбранного `$pipeline`.
