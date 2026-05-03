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
| 2. Runtime                | `bioetl-runtime`                | L2 diagnostic runtime triage: blockers, latency, backlog, error localization, handoffs     |
| Control Plane v1 | `bioetl-control-plane-v1`       | L1/L2 replay/resume safety: manifest, ledger, checkpoint, replay, lineage, global reads    |
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

1. `bioetl-overview-v2`, first-screen KPI row (no scroll):
   `System Status`, `Next Action`, `Failed Runs in Range`, `Worst Backlog Stage`,
   `Worst Lag Stage` и `Flow Balance` отвечают на L0 вопрос: что broken/degraded
   и куда открыть drilldown первым. `OK` считается здоровым только при recent
   activity; отсутствие samples остаётся `UNKNOWN`, а не зелёным нулём.
1. `bioetl-runtime`, top answer row:
   `Runtime Blockers / 15m`, `Failed Runs / 15m`, `No-Records Runs / 30m`,
   `Runtime Error Rate / 30m`, `Worst Stage Lag / 15m`,
   `Memory Pressure Active / 15m` отвечают на L2 вопрос без прокрутки.
1. `bioetl-runtime`, localization row:
   `Stage Backlog Trend`, `Records by Stage / Interval`,
   `Pipeline Phase Duration p50/p95/p99`,
   `Pipeline Duration p50/p95/p99`,
   `Errors by Stage / Error Code / Range`,
   `Records by Stage / Run Type / Range`.
1. `bioetl-control-plane-v1`, answer row:
   `Replay / Resume Blockers`, `Manifest Write Failures`,
   `Ledger Append Failures`, `Checkpoint Incompatibilities`,
   `Replay Not Reconstructable`, `Replay Drift` и `Lineage Refs Missing`
   отвечают на L1/L2 вопрос: можно ли доверять manifest/ledger/checkpoint/
   lineage state и безопасно выполнять replay/resume. Любой non-zero blocker
   требует расследования до replay/resume.
1. `bioetl-provider-health-v2`, panel `id=114`, `id=1`, `id=104`, `id=106`, `id=107`, `id=108`, `id=109`, `id=102`:
   current provider status mapping (`UNHEALTHY`/`DEGRADED`/`HEALTHY`), p95 latency trend + current p95, failure/degraded trend, provider failure share и retries exhausted.
1. `bioetl-dq-v2`, panel `id=2` (`Data Quality Score (Volume-weighted)`):
   `sum(score * record_count) / clamp_min(sum(record_count), 1)` на базе
   `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`
1. `bioetl-dq-v2`, panel `id=6`, `id=7`, `id=12`:
   range-based quarantine/threshold/failures for the active Grafana window.
1. `bioetl-overview-v2`, routing and evidence rows:
   `Runtime Status`, `Data Quality Status`, `Control Plane Status`,
   `Provider Status` и `Workflow Status` показывают status + reason + next
   dashboard вместо opaque numeric handoff. `Flow Balance` заменяет
   misleading yield gauge и показывает Bronze denominator, Gold output,
   filtered/quarantined counts и unaccounted loss. `Backlog Causality`
   кладёт backlog, lag и throughput в одну таблицу, чтобы проверить
   `backlog(t+1) = backlog(t) + ingestion - output`. Compact supporting checks
   по manifest/ledger, checkpoint, lineage и Silver rejects остаются L0-only.
1. `bioetl-workflow-overview`, panel `id=2`, `id=3`, `id=4`, `id=5`:
   declarative workflow runs, failed runs, step outcomes и step latency;
   используйте его, когда pipeline summary выглядит здоровым, но orchestration
   path показывает `failed/skipped/blocked` status.



### Screenshot map: `bioetl-overview-v2` (новая структура первого экрана)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ L0 Overview Scope                                                           │
├──────────────┬──────────────┬──────────────────┬──────────────────┬──────────┤
│ System Status│ Next Action  │ Failed Runs      │ Worst Backlog    │ Worst Lag│
│              │              │ in Range         │ Stage            │ Stage    │
├──────────────┴──────────────┴──────────────────┴──────────────────┴──────────┤
│ Flow Balance (Bronze/Gold/loss denominator context)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾ Throughput details (collapsed row by default)                              │
│ ▾ Freshness breakdown (collapsed row by default)                             │
│ ▾ Extended distributions (collapsed row by default)                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

Первый экран без скролла должен отвечать на вопрос **«что сломано и куда идти дальше»**:
- что сломано: `System Status` + `Failed Runs in Range` + `Worst Backlog/Lag Stage`;
- куда идти дальше: `Next Action` + drilldown links в KPI/reason panels;
- баланс потока: `Flow Balance` (вход/выход/потери), без скрытия деградации в single-rate KPI.
## Silver Filter Rejects workflow

- Для быстрых summary используйте `Silver Rejects Count + Rate` в
  `bioetl-overview-v2` и `Silver Filter Rejects` в `bioetl-runtime`. Overview
  intentionally не показывает standalone green reject-rate gauge: rate
  интерпретируется только рядом с Bronze denominator / activity context.
- `bioetl-overview-v2` и `bioetl-runtime` содержат явный handoff в
  `4. Data Quality`, но runtime dashboard больше не тащит в себя DQ internals:
  он показывает только compact handoff conditions.
- Для bounded cause summary используйте `Top Silver Reject Reasons` и
  `Top Silver Reject Fields` в `bioetl-dq-v2`.
- Короткая triage sequence:
  1. Начните с `1. BioETL Overview` или `2. Runtime`, чтобы подтвердить spike по
     `Silver Rejects Count + Rate` / `Silver Filter Rejects` в текущем time range.
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


## Unified Top Navigation CTA (v2)

All primary dashboards (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `6. Workflow Overview`) MUST expose the same top navigation block in this exact order:

1. `Back to Overview`
2. `Next Recommended Drilldown`
3. `Explore Logs (Loki, tracing profile)`
4. `Explore Traces (Tempo, tracing profile)`

Variable handoff policy for these links is strict and bounded:

- `includeVars=false` for every link (no implicit variable leakage).
- Pass only target-scoped variables directly in URL (`var-*`) when required by the destination dashboard.
- For overview/runtime/dq flows pass only `$pipeline/$run_type` unless destination needs another explicit scope.
- For provider flow pass only `$provider/$adapter` (or explicit `All` defaults when opening non-provider dashboards).
- Workflow-specific variables (`$workflow`, `$status`) and forensic IDs (`$run_id`, `$payload_hash`) MUST NOT be propagated into non-target dashboards.

## Default dashboard windows (L0/L1 baseline + L2 forensic exception)

- Единый baseline для operator-facing L0/L1 dashboards:
  - `overview`, `runtime`, `dq`, `control-plane`, `workflow-overview` -> `time.from=now-12h`, `refresh=30s`.
- Forensic L2 exception:
  - `silver-reject-explorer` -> `time.from=now-24h`, `refresh=1m`.
  - Justification: forensic-поиск по reject payload обычно начинается с более широкого окна и не требует 30s polling; более медленный refresh снижает ненужные перезапросы при row-level drilldown.
- Любое отклонение от baseline MUST сопровождаться явным обоснованием в документации и в PR (почему это не L0/L1 operator window).

## Drilldown

- `bioetl-overview-v2`: L0 Overview отвечает на один primary question:
  what is currently broken or degraded in BioETL, and where should the
  operator drill down first? Dashboard links `2. Runtime`,
  `Control Plane v1`, `3. Provider Health`, `4. Data Quality`,
  `6. Workflow Overview`,
  `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)`
  открывают соседние dashboards и Grafana Explore в текущем time range.
  Cross-dashboard URLs передают только target-scoped variables; provider/workflow
  dashboards не наследуют `$pipeline/$run_type` leakage. `System Status` and
  `Next Action` are the first operator answer; subsystem status cards show
  `Reason:` and `Next:` in legends. Panel `id=1`
  (`Processing Volume by Stage`) дублирует Explore handoff через data links.
- `bioetl-runtime`: top-level links `Back to Overview`, `Control Plane v1`,
  `3. Provider Health`, `4. Data Quality`, `Explore Logs (Loki, tracing profile)`,
  `Explore Traces (Tempo, tracing profile)` и `Runtime Runbook` дают явный
  routing path из L2 runtime triage. Cross-dashboard handoffs передают только
  target-scoped variables; forensic IDs в runtime dashboard запрещены.
- `bioetl-control-plane-v1`: Control Plane v1 отвечает на один
  primary question: can we trust manifest/ledger/checkpoint/lineage state and
  safely replay/resume? Первый ряд содержит только replay/resume blockers.
  Manifest/ledger ratios, checkpoint/replay diagnostics, GLOBAL reads,
  audit/lineage diagnostics и missing-signal notes расположены ниже. GLOBAL
  read-path panels не фильтруются по `$pipeline/$run_type`; это сознательно,
  потому что `bioetl_control_plane_reads_total` и
  `bioetl_control_plane_read_duration_seconds_bucket` глобальны по
  `store/operation/status`.
- `bioetl-provider-health-v2`: dashboard links `Back to Overview`, `2. Runtime`, `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают быстрый переход из provider health surface в runtime/overview и correlation flow без ложного pipeline scope в target dashboards. Panel `id=114` (`Current Provider Health Status`) показывает явный enum mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`, а panel `id=1` (`Health Check Latency by Provider (p95)`) дублирует Explore handoff через data links.
- `bioetl-dq-v2`: dashboard link `Back to Overview` плюс `5. Silver Reject Explorer`, `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)` дают тот же переход для DQ incidents и freshness investigation. Handoff в Explorer передаёт только bounded `$pipeline/$run_type` scope, а не generic `includeVars` leakage. Panel `id=1` (`Data Flow in Range: Bronze -> Silver -> Gold`) дублирует Explore handoff через data links.
- `bioetl-silver-reject-explorer`: dashboard links `Back to Overview`, `Back to Data Quality`, `Open Logs`, `Open Traces`; back-links возвращают только `$pipeline/$run_type`, не leaking `payload_hash` или other forensic filters. Main table поддерживает data links для self-drilldown по `payload_hash` и CLI handoff.
- `bioetl-workflow-overview`: dashboard links `Back to Overview`, `2. Runtime`, `Control Plane v1`; cross-dashboard handoffs не leaking `$workflow/$status` into non-workflow targets. Prometheus panels use only bounded workflow labels (`workflow`, `status`, `step_kind`) and never require `run_id`/`step_id` labels.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: dashboards с `$pipeline/$run_type` предварительно фильтруют TraceQL по `span."bioetl.pipeline"` и `span."bioetl.run_type"`, а provider dashboard — по `span."bioetl.provider"`. Это не заменяет correlation по `trace_id` / `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом клике.
- `bioetl-runtime` row `Tracing-only Log Hygiene` теперь включает table panel `Alert-to-Action Map` как runbook-lite:
  - `warning_spike` -> вероятная причина: provider instability или DQ threshold drift; следующий шаг: `docs/05-operations/runbooks/dq-failure-investigation.md`.
  - `unstructured_logs_growth` -> вероятная причина: parser/schema drift или не-JSON logger output; следующий шаг: `docs/05-operations/runbooks/incident-response.md` (provider triage).
  - `hygiene_anomaly` -> вероятная причина: runtime-control mismatch/checkpoint lag/stale state; следующий шаг: `docs/05-operations/runbooks/run-manifest-inspection.md`.
  Семантика окна для карты: сигналы читаются в том же active Grafana time range (`$__range`), а trend panel в этом ряду использует `$__interval`; это согласовано с rule-pack потому что condition-summary panels в runtime остаются на `increase(...[$__range])` и не смешивают fixed 30m window с log-hygiene triage.

- Runtime condition-summary triage path:
  `Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `DQ Alert Conditions` / `Freshness Alert Conditions` -> `dq-failure-investigation.md`,
  `Control-plane Alert Conditions` -> `run-manifest-inspection.md`,
  `GLOBAL Provider Alert Conditions` -> `incident-response.md`,
  `No-Records Runs / 30m` -> `checkpoint-debugging.md`.

- Known missing runtime panels:
  `Retry vs Failure` и `Batch Size Distribution` не shipped, пока repo не
  подтверждает bounded runtime metric family для этих решений.

## Важные пороги (из JSON)

- `overview.System Status`: `BROKEN` при failed runs `>0`, stage backlog `>0`,
  worst lag `>=300s`, DQ hard fail `>0` или control-plane blocker `>0`;
  `DEGRADED` при warning-сигналах provider/DQ/freshness/workflow; `UNKNOWN`
  при отсутствии recent activity/samples; `OK` только при recent activity и
  отсутствии blockers/warnings.
- `overview.Next Action`: runtime имеет приоритет над DQ, control-plane,
  provider и workflow, чтобы backlog/lag immediately route в `2. Runtime`.
- `overview.Flow Balance`: не является health gauge; Bronze denominator `0`
  означает `No recent input` / yield unavailable, а не зелёный `100%`.
- `control-plane.Replay / Resume Blockers`: green `0`, red `>=1`; non-zero
  означает block replay/resume до расследования manifest/ledger/checkpoint/
  replay/lineage signal.
- `control-plane.Manifest/Ledger Failure Ratio`: green `0`, yellow `>0`,
  red `>0.10` за фиксированное окно `30m`.
- `control-plane.GLOBAL Control-Plane Read Failure Ratio`: green `0`,
  yellow `>0`, red `>0.05` за фиксированное окно `30m`.
- `control-plane latency p50/p95/p99`: histogram-backed panels сохраняют
  `No data` как diagnostic signal; отсутствие samples не превращается в `0s`.
- `control-plane.Known Missing Replay-Safety Signals`: checkpoint age vs RPO
  и replay duplicate detection документируются как отсутствующие метрики, а не
  подменяются fake PromQL.
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
