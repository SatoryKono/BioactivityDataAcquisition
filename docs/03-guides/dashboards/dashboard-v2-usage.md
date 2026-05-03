______________________________________________________________________

Version: 1.3.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-13'

______________________________________________________________________

# BioETL Dashboards v2: Usage

Дата сверки: **2026-04-13**
Источник истины: `grafana/dashboards/*.json`

## Какие дашборды использовать

| Dashboard                 | UID                             | Для чего                                                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 1. BioETL Overview        | `bioetl-overview-v2`            | L0 answer-first dashboard: что сейчас сломано/degraded и куда drill down дальше |
| 2. Runtime                | `bioetl-runtime`                | Runtime triage: warnings, unstructured logs, adaptive-memory signals, alert conditions     |
| 3. Provider Health        | `bioetl-provider-health-v2`     | Incident triage по provider health: latency/failures/degraded/retries exhausted            |
| 4. Data Quality           | `bioetl-dq-v2`                  | Качество данных, карантин, аномалии, freshness                                             |
| 5. Silver Reject Explorer | `bioetl-silver-reject-explorer` | Record-level explorer для `filtered_out`/`FILTERED_OUT_SILVER` записей (quarantine-backed) |
| 6. Workflow Overview      | `bioetl-workflow-overview`      | Declarative workflow run/step outcomes and transform-step latency                          |

## Фильтрация

- `bioetl-overview-v2`: `$pipeline`, `$run_type`
- `bioetl-control-plane-v1`: `$pipeline`, `$run_type`
- `bioetl-dq-v2`, `bioetl-runtime`: `$pipeline`, `$run_type`, `$stage`
- `bioetl-provider-health-v2`: `$provider`, `$adapter`
- `bioetl-silver-reject-explorer`: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash`
- Для `bioetl-silver-reject-explorer` `$pipeline` должен быть scoped
  single-select (без `All`), потому что quarantine API fail-closed требует
  явный `pipeline` параметр.
- Переменная `execution` не используется; `$run_id` и `$payload_hash`
  используются только в `bioetl-silver-reject-explorer` как Explorer-only
  forensic filters, а не как Prometheus labels.

## Что смотреть в первую очередь

1. `bioetl-overview-v2`, top answer row:
   `Failed Pipeline Runs`, `Overall Yield`, `Active Stage Backlog`,
   `Worst Stage Lag`, `DQ Blocking`, `Control Plane Unsafe` и
   `Provider Degraded` отвечают на L0 вопрос: что broken/degraded и куда
   открыть drilldown первым.
1. `bioetl-runtime`, panel `id=2`, `id=3`, `id=4`, `id=5`, `id=6`, `id=7`:
   warnings, unstructured logs и alert-condition сигналы по DQ/control-plane/provider/freshness.
1. `bioetl-runtime`, panel `id=18`, `id=19`, `id=20`, `id=21`:
   adaptive-memory triage: pressure events, resize events, fallback monitor decisions и бинарный pressure-active signal.
1. `bioetl-provider-health-v2`, panel `id=114`, `id=1`, `id=104`, `id=106`, `id=107`, `id=108`, `id=109`, `id=102`:
   current provider status mapping (`UNHEALTHY`/`DEGRADED`/`HEALTHY`), p95 latency trend + current p95, failure/degraded trend, provider failure share и retries exhausted.
1. `bioetl-dq-v2`, panel `id=2` (`Data Quality Score (Volume-weighted)`):
   `sum(score * record_count) / clamp_min(sum(record_count), 1)` на базе
   `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`
1. `bioetl-dq-v2`, panel `id=6`, `id=7`, `id=12`:
   range-based quarantine/threshold/failures for the active Grafana window.
1. `bioetl-overview-v2`, handoff/failure rows:
   `Runtime Handoff`, `Data Quality Handoff`, `Control Plane Handoff`,
   `Provider Handoff`, `Workflow Handoff` и compact summaries по manifest/ledger,
   checkpoint, lineage и Silver rejects. Composite source-selection detail
   вынесен из L0 flow в Control Plane diagnostics.
1. `bioetl-workflow-overview`, panel `id=2`, `id=3`, `id=4`, `id=5`:
   declarative workflow runs, failed runs, step outcomes и step latency;
   используйте его, когда pipeline summary выглядит здоровым, но orchestration
   path показывает `failed/skipped/blocked` status.

## Silver Filter Rejects workflow

- Для быстрых summary используйте shipped panels `Silver Filter Rejects` и
  `Silver Filter Reject Rate` в `bioetl-overview-v2`, а detailed bounded
  breakdown смотрите в `bioetl-dq-v2` / `bioetl-runtime`.
- `bioetl-overview-v2` и `bioetl-runtime` теперь содержат явный handoff в
  `4. Data Quality`, чтобы оператор мог быстро перейти от summary spike к
  bounded cause breakdown.
- Для bounded cause summary используйте `Top Silver Reject Reasons` и
  `Top Silver Reject Fields` в `bioetl-dq-v2`.
- Короткая triage sequence:
  1. Начните с `1. BioETL Overview` или `2. Runtime`, чтобы подтвердить spike по
     `Silver Filter Rejects` в текущем time range.
  1. Перейдите в `4. Data Quality` и проверьте `Top Silver Reject Reasons` /
     `Top Silver Reject Fields`, чтобы сузить проблему до bounded cause summary.
  1. Откройте `5. Silver Reject Explorer` для record-level списка, выбора
     `reason_code/field/run_id` и detail по конкретному `payload_hash`.
  1. Используйте quarantine CLI для action-операций (`replay/resolve/purge`) и
     финального подтверждения remediation.
- Эти панели отвечают на вопросы:
  - растёт ли объём `filtered_out`;
  - в каком `$pipeline` проблема сильнее;
  - это локальный всплеск или устойчивый тренд в выбранном time range;
  - какие `reason_code` и `field` сейчас доминируют в bounded dashboard summary.
- Для action-перехода из explorer в CLI используйте:
  ```bash
  bioetl quarantine inspect --pipeline <pipeline> --silver-filter-only --run-id <run-id> --limit 200
  bioetl quarantine resolve --pipeline <pipeline> --payload-hash <payload-hash> --status IGNORED
  ```
- Grafana в shipped конфигурации разделена по ролям:
  `1-4` dashboards дают summary/trend и bounded breakdown на Prometheus.
  `5. Silver Reject Explorer` даёт row-level browsing через datasource `Quarantine Explorer`.
- Record-level drilldown больше не ограничен только CLI.
  CLI остаётся execution surface для replay/resolve/purge.

## Drilldown

- `bioetl-overview-v2`: L0 Overview отвечает на один primary question:
  what is currently broken or degraded in BioETL, and where should the
  operator drill down first? Dashboard links `2. Runtime`, `Control Plane v1`,
  `3. Provider Health`, `4. Data Quality`, `6. Workflow Overview`,
  `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)`
  открывают соседние dashboards и Grafana Explore в текущем time range.
  Cross-dashboard URLs передают только target-scoped variables; provider/workflow
  dashboards не наследуют `$pipeline/$run_type` leakage. Panel `id=1`
  (`Processing Volume by Stage`) дублирует Explore handoff через data links.
- `bioetl-runtime`: dashboard link `Back to Overview` плюс `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают короткий путь из warning/unstructured-log spikes, adaptive-memory regressions и alert spikes обратно в overview и в Explore. Dashboard handoffs передают только `$pipeline/$run_type` для runtime-compatible targets. Panel `id=9` (`Log Hygiene Trend`) дублирует Explore handoff через data links, а `Pipeline/DQ/Control-plane/Provider/Freshness Alert Conditions` теперь дают прямые runbook links для следующего operator шага.
- `bioetl-provider-health-v2`: dashboard links `Back to Overview`, `2. Runtime`, `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают быстрый переход из provider health surface в runtime/overview и correlation flow без ложного pipeline scope в target dashboards. Panel `id=114` (`Current Provider Health Status`) показывает явный enum mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`, а panel `id=1` (`Health Check Latency by Provider (p95)`) дублирует Explore handoff через data links.
- `bioetl-dq-v2`: dashboard link `Back to Overview` плюс `5. Silver Reject Explorer`, `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают тот же переход для DQ incidents и freshness investigation. Handoff в Explorer передаёт только bounded `$pipeline/$run_type` scope, а не generic `includeVars` leakage. Panel `id=1` (`Data Flow in Range: Bronze -> Silver -> Gold`) дублирует Explore handoff через data links.
- `bioetl-silver-reject-explorer`: dashboard links `Back to Overview`, `Back to Data Quality`, `Open Logs`, `Open Traces`; back-links возвращают только `$pipeline/$run_type`, не leaking `payload_hash` или other forensic filters. Main table поддерживает data links для self-drilldown по `payload_hash` и CLI handoff.
- `bioetl-workflow-overview`: dashboard links `Back to Overview`, `2. Runtime`, `Control Plane v1`; cross-dashboard handoffs не leaking `$workflow/$status` into non-workflow targets. Prometheus panels use only bounded workflow labels (`workflow`, `status`, `step_kind`) and never require `run_id`/`step_id` labels.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: dashboards с `$pipeline/$run_type` предварительно фильтруют TraceQL по `span."bioetl.pipeline"` и `span."bioetl.run_type"`, а provider dashboard — по `span."bioetl.provider"`. Это не заменяет correlation по `trace_id` / `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом клике.
- Runtime condition-summary triage path:
  `Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `DQ Alert Conditions` / `Freshness Alert Conditions` -> `dq-failure-investigation.md`,
  `Control-plane Alert Conditions` -> `run-manifest-inspection.md` / `observability-checklist.md`,
  `Provider Alert Conditions` -> `incident-response.md`.

## Важные пороги (из JSON)

- `overview.answer row`: Failed pipeline/DQ/control-plane red `>=1`; backlog
  yellow `>0`; lag yellow `>=300s`; provider degradation yellow/red non-zero.
- `overview.id=4`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=5`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=8`: yellow `>=3600s`, red `>=21600s`; gauge now shows the worst stale entity in scope, not the freshest timestamp
- `overview.id=111`: yellow `>=1`, red `>=5`
- `overview.id=113`: yellow `>=1`, red `>=5`
- `overview.id=114`: yellow `>=1`, red `>=10`
- `provider.id=104`: yellow `>=5%`, red `>=20%`
- `provider.id=102`: yellow `>=0.5s`, orange `>=2s`, red `>=5s`

## Частые проблемы

1. `No data`:
   проверьте `http://localhost:8000/metrics`, затем `http://localhost:9090/targets`.
1. `No data` на p95 latency panels:
   это диагностический сигнал “нет latency samples / probes / scrape window”, а
   не `0s latency`. Сначала проверьте activity/count panels рядом, потом уже
   datasource health.
1. Пустой `$provider`:
   нет ни одной серии `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`
   или `bioetl_health_check_failures_total` в metrics endpoint.
1. Пустой `$run_type`:
   нет метрик `bioetl_records_processed_total` для выбранного `$pipeline`.
1. `bioetl-silver-reject-explorer` показывает plugin error или `No data`:
   проверьте, что выбран конкретный `$pipeline` (не `All`) и что backend отвечает на
   `/ops/quarantine/filter-options?pipeline=<pipeline_name>`.
