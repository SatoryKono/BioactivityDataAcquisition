---
Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-05'
---

# BioETL Dashboards v2: Usage

Дата сверки: **2026-04-05**
Источник истины: `grafana/dashboards/*.json`

## Какие дашборды использовать

| Dashboard | UID | Для чего |
|---|---|---|
| 1. Overview | `bioetl-overview-v2` | Общее состояние пайплайна, control-plane и lineage health |
| 2. Runtime | `bioetl-runtime` | Runtime triage: warnings, unstructured logs, alert conditions |
| 3. Provider Health | `bioetl-provider-health-v2` | Latency/успехи health_check провайдеров |
| 4. Data Quality | `bioetl-dq-v2` | Качество данных, карантин, аномалии, freshness |

## Фильтрация

- `bioetl-overview-v2`, `bioetl-dq-v2`, `bioetl-runtime`: `$pipeline`, `$run_type`
- `bioetl-provider-health-v2`: `$provider`
- Переменные `$run_id` и `execution` не используются.

## Что смотреть в первую очередь

1. `bioetl-overview-v2`, panel `id=4` (`Overall Yield (Selected Range)`):
`sum(increase(gold[$__range])) / clamp_min(sum(increase(bronze[$__range])), 1)`
2. `bioetl-runtime`, panel `id=2`, `id=3`, `id=4`, `id=5`, `id=6`, `id=7`:
warnings, unstructured logs и alert-condition сигналы по DQ/control-plane/provider/freshness.
3. `bioetl-provider-health-v2`, panel `id=1`, `id=104`, `id=2`, `id=7`, `id=102`:
p95 latency, failure-rate и 15-минутный объём health checks по провайдерам.
4. `bioetl-dq-v2`, panel `id=2` (`Data Quality Score (Volume-weighted)`):
`sum(score * record_count) / clamp_min(sum(record_count), 1)` на базе
`bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`
5. `bioetl-dq-v2`, panel `id=6`, `id=7`, `id=12`:
range-based quarantine/threshold/failures for the active Grafana window.
6. `bioetl-overview-v2`, panel `id=111`, `id=112`, `id=113`, `id=114`, `id=120`, `id=115`:
manifest/ledger failures, checkpoint incompatibilities, missing lineage refs,
composite source selections и fragment outcomes по `layer/status`.

## Silver Filter Rejects workflow

- Для быстрых summary используйте shipped panels `Silver Filter Rejects` и
  `Silver Filter Rejects by Pipeline` в `bioetl-overview-v2`, `bioetl-dq-v2`,
  `bioetl-runtime`.
- `bioetl-overview-v2` и `bioetl-runtime` теперь содержат явный handoff в
  `4. Data Quality`, чтобы оператор мог быстро перейти от summary spike к
  bounded cause breakdown.
- Для bounded cause summary используйте `Top Silver Reject Reasons` и
  `Top Silver Reject Fields` в `bioetl-dq-v2`.
- Эти панели отвечают на вопросы:
  - растёт ли объём `filtered_out`;
  - в каком `$pipeline` проблема сильнее;
  - это локальный всплеск или устойчивый тренд в выбранном time range;
  - какие `reason_code` и `field` сейчас доминируют в bounded dashboard summary.
- Для ответа на вопрос "почему именно записи были исключены" переходите в CLI:
  ```bash
  bioetl quarantine stats --pipeline <pipeline> --silver-filter-only
  bioetl quarantine stats --pipeline <pipeline> --silver-filter-only --group-by reason-code-field
  bioetl quarantine stats --pipeline <pipeline> --silver-filter-only --group-by reason-signature
  bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --limit 20
  ```
- Grafana в текущей shipped конфигурации — summary/trend surface.
  `Top Silver Reject Reasons` / `Top Silver Reject Fields` используют bounded
  metric vocabulary, а не raw quarantine text.
- Record-level причины и exact by-reason drilldown остаются задачей quarantine CLI.

## Drilldown

- `bioetl-overview-v2`: dashboard links `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` открывают соседние dashboards и Grafana Explore в текущем time range. Panel `id=1` (`Processing Volume by Stage`) дублирует Explore handoff через data links.
- `bioetl-runtime`: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают короткий путь из warning/unstructured-log spikes обратно в overview и в Explore. Panel `id=9` (`Log Hygiene Trend`) дублирует Explore handoff через data links.
- `bioetl-provider-health-v2`: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают быстрый переход из provider health surface в overview и correlation flow. Panel `id=1` (`Health Check Latency by Provider (p95)`) дублирует Explore handoff через data links.
- `bioetl-dq-v2`: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают тот же переход для DQ incidents и freshness investigation. Panel `id=1` (`Data Flow in Range: Bronze -> Silver -> Gold`) дублирует Explore handoff через data links.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: dashboards с `$pipeline/$run_type` предварительно фильтруют TraceQL по `span."bioetl.pipeline"` и `span."bioetl.run_type"`, а provider dashboard — по `span."bioetl.provider"`. Это не заменяет correlation по `trace_id` / `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом клике.

## Важные пороги (из JSON)

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
нет ни одной серии `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`
или `bioetl_health_check_failures_total` в metrics endpoint.
3. Пустой `$run_type`:
нет метрик `bioetl_records_processed_total` для выбранного `$pipeline`.
