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

Machine-readable navigation contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (docs/tests должны соответствовать ему).

## Какие дашборды использовать

| Dashboard                 | UID                             | Для чего                                                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 0. Control Plane          | `bioetl-control-plane-v1`       | L1/L2 replay/resume safety: manifest, ledger, checkpoint, replay, lineage, global reads    |
| 1. Overview               | `bioetl-overview-v2`            | L0 answer-first dashboard: что сейчас сломано/degraded и куда drill down дальше            |
| 2. Runtime                | `bioetl-runtime`                | L2 diagnostic runtime triage: blockers, latency, backlog, error localization, handoffs     |
| 3. Provider Health        | `bioetl-provider-health-v2`     | Incident triage по provider health: latency/failures/degraded/retries exhausted            |
| 4. Data Quality           | `bioetl-dq-v2`                  | Качество данных, карантин, аномалии, freshness                                             |
| Silver Reject Explorer    | `bioetl-silver-reject-explorer` | Record-level explorer для `filtered_out`/`FILTERED_OUT_SILVER` записей (quarantine-backed) |
| 5. Workflow               | `bioetl-workflow-overview`      | Selected-range declarative workflow run/step evidence and transform-step latency handoff   |

## From where to enter each dashboard in 1 click

| Target dashboard | 1-click entry source |
| --- | --- |
| `bioetl-control-plane-v1` | top-level `0. Control Plane` from every primary dashboard except itself |
| `bioetl-overview-v2` | top-level `1. Overview` from every primary dashboard except itself |
| `bioetl-runtime` | top-level `2. Runtime` from every primary dashboard except itself |
| `bioetl-provider-health-v2` | top-level `3. Provider Health` from every primary dashboard except itself |
| `bioetl-dq-v2` | top-level `4. Data Quality` from every primary dashboard except itself |
| `bioetl-workflow-overview` | top-level `5. Workflow` from every primary dashboard except itself |
| `bioetl-silver-reject-explorer` | top-level `Silver Reject Explorer` from `4. Data Quality` only |

## Фильтрация

- `bioetl-overview-v2`: `$pipeline`, `$run_type`
- `bioetl-control-plane-v1`: `$pipeline`, `$run_type`
- `bioetl-dq-v2`, `bioetl-runtime`: `$pipeline`, `$run_type`, `$stage`
- `bioetl-provider-health-v2`: `$provider`, hidden `$pipeline_context`, `$adapter`
- `bioetl-silver-reject-explorer`: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash`
- `$pipeline` и `$provider` всегда single-select без `All`; если исходного
  контекста нет, используется explicit fallback `unknown`.
- `$run_type` всегда имеет include-all fallback; если исходного run-type
  контекста нет, используйте `Run Type=All`, а не `unknown`.
- Переходы в `3. Provider Health` из pipeline-scoped dashboards вычисляют
  `$provider` из текущего `$pipeline` и сохраняют `$pipeline_context` для
  обратного перехода.
- Для `bioetl-silver-reject-explorer` `$pipeline` также остаётся scoped
  single-select, потому что quarantine API fail-closed требует явный
  `pipeline` параметр.
- Переменная `execution` не используется; `$run_id` и `$payload_hash`
  используются только в `bioetl-silver-reject-explorer` как Explorer-only
  forensic filters, а не как Prometheus labels.

## Что смотреть в первую очередь

1. `bioetl-overview-v2`, first-screen KPI row (no scroll):
   `System Status`, `Next Action` и `L0 Inputs` отвечают на L0 вопрос: что
   broken/degraded и куда открыть drilldown первым. `OK` считается здоровым
   только при recent activity; отсутствие samples остаётся `UNKNOWN`, а не
   зелёным нулём.
1. `bioetl-runtime`, first-screen answer row (без скролла):
   `First Action`, `Monitor Runtime Current Status`, `Monitor Runtime Blockers` и
   `Inspect Top Runtime Blockers` отвечают на L2 вопрос «что блокирует
   выполнение сейчас и куда идти дальше». Selected-range evidence начинается
   ниже и не определяет current status.
1. `bioetl-runtime`, collapsed row-группы по сценарию:
   `Backlog Trends`, `Durations`, `Shutdown Diagnostics`,
   `Tracing-only Log Hygiene`. Открывайте ровно одну нужную группу после
   чтения summary KPI, чтобы сократить шум первого экрана.
1. `bioetl-control-plane-v1`, answer row:
   `Monitor: Replay Safety State`, `Inspect: Known Gap - Checkpoint Freshness`,
   `Monitor: Ledger / Manifest Consistency` и `Inspect: Control-Plane Telemetry Missing`
   отвечают на L1/L2 вопрос: можно ли доверять
   manifest/ledger/checkpoint/lineage state и безопасно выполнять
   replay/resume прямо сейчас. Любой non-zero current-signal требует расследования
   до replay/resume; non-zero/UNKNOWN telemetry-missing risk означает, что зелёные
   нули нельзя считать доказательством безопасности. `Track: Replay / Resume Blockers in Range`
   и `Inspect: Terminal Run Events by Status in Range` вынесены ниже как
   selected-range evidence, а не first-screen verdict. Replay/checkpoint
   runbook path здесь canonical через `checkpoint-debugging.md`; exact
   manifest/ledger identity evidence остаётся surface `run-manifest-inspection.md`.
1. `bioetl-provider-health-v2`, first-screen GLOBAL answer row:
   `GLOBAL Provider Scope`, `Monitor GLOBAL Provider Severity Matrix`,
   `Inspect Critical Providers`, `Inspect Provider Top Causes` и `First Action`
   отвечают на вопрос «какой provider degraded/failing и почему». Panel `id=114`
   остаётся raw source enum (`0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`) ниже
   first screen как evidence.
1. `bioetl-dq-v2`, first-screen answer row:
   `Monitor DQ Current Status`, `Monitor DQ Threshold State`,
   `Inspect DQ Current Reasons` и `First Action / Invalid Record Policy`
   отвечают на вопрос «DQ сейчас OK/DEGRADED/FAILING/UNKNOWN и какое действие
   первое». Это pipeline-wide 15m snapshot; `$run_type` и stage filters ниже
   управляют только selected-range evidence. `Data Quality Score
   (Volume-weighted)`, quarantine, Silver rejects и flow остаются
   selected-range evidence ниже.
1. `bioetl-overview-v2`, routing and evidence rows:
   `Runtime Blockers Current`, `DQ Status Current`, `Gold Lifecycle Current`,
   `Control Plane Current`, `Provider GLOBAL Scope`, `Workflow Selected Scope`,
   и `Workflow GLOBAL Scope` показывают current-only operator state с явным
   scope. Status tables use row-wide threshold coloring, а не только окраску
   ячейки `Status`. Исторические счётчики вынесены в collapsed row
   `Range Evidence (Historical / Recent History)`, а `Diagnostics & Docs (Logs / Traces / Raw Metrics)`
   содержит routing по logs/traces/raw metrics.
1. `bioetl-workflow-overview`, panels `id=2`, `id=3`, `id=6`, `id=7`, `id=4`,
   `id=5`, `id=8`:
   selected-range declarative workflow evidence for failed runs, failed/skipped
   step events, run-outcome mix, step outcomes, и step latency. Используйте его,
   когда нужен bounded workflow evidence layer, но для current stage/run_id,
   replay/resume или provider/DQ root cause переходите дальше по top-level bus.

## Incident first steps (Runtime top navigation)

В `2. Runtime` cross-dashboard routing выполняется только через top-level bus:
`0. Control Plane`, `1. Overview`, `3. Provider Health`, `4. Data Quality`,
`5. Workflow`, `Explore Logs`, `Explore Traces`.

Panel-level dashboard handoffs и `First Action` dashboard CTAs намеренно
отсутствуют, чтобы не создавать второй путь в тот же target dashboard. Для
быстрого старта triage сначала выберите домен инцидента через top-level bus,
затем используйте detail/condition cards внутри выбранного dashboard.



### Screenshot map: `bioetl-overview-v2` (новая структура первого экрана)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ L0 Overview Scope                                                           │
├──────────────┬──────────────────────┬────────────────────────────────────────┤
│ System Status│ Next Action          │ L0 Inputs                              │
├──────────────┼──────────────┬───────┼──────────────┬─────────────────────────┤
│ Runtime      │ DQ Status    │ Gold  │ Control Plane│ Provider/Workflow scope │
│ Blockers     │ Current      │ Life- │ Current      │ tables                  │
│ Current      │              │ cycle │              │                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾ Range Evidence (collapsed row by default)                                  │
│ ▾ Diagnostics & Docs (Logs / Traces / Raw Metrics) (collapsed row by default)│
└──────────────────────────────────────────────────────────────────────────────┘
```

Первый экран без скролла должен отвечать на вопрос **«что сломано и куда идти дальше»**:
- что сломано: `System Status` + `L0 Inputs` + L1 current tables;
- куда идти дальше: `Next Action` с `action_target/action_reason/action_dashboard_uid`;
- что было в окне времени: collapsed `Range Evidence`;
- где искать сырые traces/logs/metrics: collapsed `Diagnostics & Docs (Logs / Traces / Raw Metrics)`.
## Silver Filter Rejects workflow

- Для быстрых summary используйте `Silver Rejects Count + Rate` в
  `bioetl-overview-v2` и `Silver Filter Rejects` в `bioetl-runtime`. Overview
  intentionally не показывает standalone green reject-rate gauge: rate
  интерпретируется только рядом с Bronze denominator / activity context.
- `bioetl-overview-v2` и `bioetl-runtime` содержат явный handoff в
  `4. Data Quality`, но runtime dashboard больше не тащит в себя DQ internals:
  он показывает только compact handoff conditions.
- Для current-state narrowing используйте `Inspect DQ Current Reasons`; для
  bounded cause summary используйте `Top Silver Reject Reasons` и
  `Top Silver Reject Fields` в collapsed rows `bioetl-dq-v2`.
- Маршрут triage: **L1 summary -> L2 explorer**.
  1. **L1 summary:** начните с `4. Data Quality` (first-screen current status,
     threshold state, reasons, invalid-record-policy note), чтобы определить
     severity и первое действие.
  1. **L1 cause narrowing:** раскройте collapsed rows `Reject / Pareto / Fields` и `Validation Diagnostics`, проверьте `Top Silver Reject Reasons` / `Top Silver Reject Fields` и связанные diagnostics.
  1. **L2 explorer:** откройте `Silver Reject Explorer` через top-level link в `4. Data Quality` для record-level списка, выбора `reason_code/field/run_id` и detail по `payload_hash`.
  1. **L2 no-data gate:** считайте `0` rejects нормой только когда `First Action / No-Data Semantics` подтверждает конкретный pipeline, доступный Quarantine Explorer и ненулевой Bronze denominator; plugin errors, `unknown` pipeline или `bronze_records=0` остаются UNKNOWN.
  1. Используйте quarantine CLI для action-операций (`replay/resolve/purge`) и финального подтверждения remediation.
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
  `Silver Reject Explorer` даёт row-level browsing через datasource `Quarantine Explorer`.
- Record-level drilldown больше не ограничен только CLI.
  CLI остаётся execution surface для replay/resolve/purge.


## Unified Top Navigation CTA (v2)

Primary dashboards MUST follow the canonical navigation contract in
`navigation-contract.md` and the machine-readable
`contracts/navigation-links.yaml`.

The top-level dashboard bus is:
`0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
`4. Data Quality`, `5. Workflow`. Each page shows all bus links except its own
page. Any duplicate dashboard-to-dashboard link from one dashboard to the same
target dashboard is forbidden.

`Explore Logs` and `Explore Traces` are available only on `2. Runtime` and
`4. Data Quality`. `Silver Reject Explorer` is available only on
`4. Data Quality`.

Variable handoff policy for dashboard links remains strict and bounded:

- `includeVars=false` for every link (no implicit variable leakage).
- Pass only target-scoped variables directly in URL (`var-*`) when required by the destination dashboard.
- For overview/runtime/dq flows pass only `$pipeline/$run_type` unless destination needs another explicit scope.
- For provider flow pass only `$provider/$adapter` (or explicit `All` defaults when opening non-provider dashboards).
- Workflow-specific variables (`$workflow`, `$status`) and forensic IDs (`$run_id`, `$payload_hash`) MUST NOT be propagated into non-target dashboards.
- Top-level links дополнительно маркируются приоритетом (`primary`, `secondary`, `contextual`) через contract block `top_level_link_priority_by_uid`; приоритет должен быть виден в `title`/`tooltip` для неоднозначных маршрутов.

## Default dashboard windows (L0/L1 baseline + L2 forensic exception)

- Единый baseline для operator-facing L0/L1 dashboards:
  - `overview`, `runtime`, `dq`, `control-plane`, `workflow-overview` -> `time.from=now-12h`, `refresh=30s`.
- Forensic L2 exception:
  - `silver-reject-explorer` -> `time.from=now-24h`, `refresh=1m`.
  - Justification: forensic-поиск по reject payload обычно начинается с более широкого окна и не требует 30s polling; более медленный refresh снижает ненужные перезапросы при row-level drilldown.
- Любое отклонение от baseline MUST сопровождаться явным обоснованием в документации и в PR (почему это не L0/L1 operator window).
- Machine-readable contract source: `docs/03-guides/dashboards/contracts/navigation-links.yaml` -> `default_time_refresh_policy` + `default_time_refresh_policy_exceptions` (for explicit, justified deviations).


## Drilldown

- `bioetl-overview-v2`: L0 Overview отвечает на один primary question:
  what is currently broken, warning, or unknown in BioETL, and where should the
  operator drill down first? Top-level dashboard links follow the `0..5` bus
  and do not duplicate panel-level dashboard links.
  Cross-dashboard URLs передают только target-scoped variables; provider/workflow
  dashboards не наследуют `$pipeline/$run_type` leakage. `System Status` and
  `Next Action` are the first operator answer and both stay in the selected
  `$pipeline/$run_type` scope; subsystem status cards show `Reason:` and
  `Next:` in legends.

## First 2 clicks scenario (operator)

1. **Click #1:** открыть `bioetl-overview-v2`, прочитать `System Status` + `Next Action`.
2. **Click #2:** открыть рекомендуемый dashboard из top-level bus (`0. Control Plane`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`).

Цель сценария: root-cause направление должно быть определено максимум за 2 клика без обязательной прокрутки по нечастым CTA.
- `bioetl-runtime`: top-level links `0. Control Plane`, `1. Overview`,
  `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `Explore Logs`,
  `Explore Traces` дают явный
  routing path из L2 runtime triage. Cross-dashboard handoffs передают только
  target-scoped variables; forensic IDs в runtime dashboard запрещены.
- `bioetl-control-plane-v1`: `0. Control Plane` отвечает на один
  primary question: can we trust manifest/ledger/checkpoint/lineage state and
  safely replay/resume? Cross-dashboard routing is handled only by the top-level
  bus; panel-level dashboard handoffs are intentionally absent.
  Переход в `3. Provider Health` передаёт `provider=$pipeline` и
  `pipeline_context=$pipeline`, но не передаёт `adapter`, чтобы target dashboard
  использовал собственный fallback `All adapters`.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-control-plane-v1`, проверить `Monitor: Replay Safety State` (`id=891`), `Inspect: Control-Plane Telemetry Missing` (`id=907`) и `Next Action: Replay Safety Diagnostics` (`id=906`).
  2. Click #2: перейти через top-level bus в `2. Runtime` (если есть активный blocker) или `4. Data Quality` (если blocker связан с downstream quality symptoms). На первом экране оставлены только current-status Trust KPI: `id=891..893`, `id=907` и единый CTA `id=906`; `Track: Replay / Resume Blockers in Range` (`id=130`) и `Inspect: Terminal Run Events by Status in Range` (`id=908`) остаются below-fold range evidence.
  Все остальные control-plane метрики перенесены в collapsed incident rows.
  Рекомендованный operator path: сначала проверить blocker cards, затем открыть
  ровно один collapsed diagnostic row под конкретный incident-pattern.
  Порядок row-блоков стандартизирован по частоте инцидентов: `Checkpoint/Replay`
  -> `Manifest/Ledger` -> `Global Control Plane` -> `Audit/Lineage` ->
  `Known Missing Signals`. GLOBAL read-path panels не
  фильтруются по `$pipeline/$run_type`; это сознательно, потому что
  `bioetl_control_plane_reads_total` и
  `bioetl_control_plane_read_duration_seconds_bucket` глобальны по
  `store/operation/status`.
- `bioetl-provider-health-v2`: dashboard links `0. Control Plane`,
  `1. Overview`, `2. Runtime`, `4. Data Quality`, `5. Workflow` дают быстрый
  переход из provider health surface без дублирования Runtime variants.
  Panel `id=114` (`Monitor Current Provider Health Status`) показывает явный enum
  mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`.
  
  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-provider-health-v2`, проверить `Monitor Current Provider Health Status` (`id=114`) и `Health Check Latency by Provider (p95)` (`id=1`).
  2. Click #2: перейти в `2. Runtime` при active degradation/failure trend или
     в `0. Control Plane` при симптомах retry exhaustion/state inconsistency.
- `bioetl-dq-v2`: dashboard links `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `5. Workflow`, `Silver Reject Explorer`,
  `Explore Logs`, `Explore Traces` дают переходы для DQ incidents и freshness
  investigation. Handoff в Explorer передаёт только bounded `$pipeline/$run_type`
  scope, а не generic `includeVars` leakage.
- `bioetl-silver-reject-explorer`: dashboard bus links `0..5`; no Explore links
  and no self-link to Silver Reject Explorer. Main table поддерживает data links
  для self-drilldown по `payload_hash` и CLI handoff. Верхняя explanatory panel
  явно показывает banner `default 24h forensic window`, чтобы оператор не
  интерпретировал explorer как обычное `now-12h` окно.

### Expected operator behavior for DQ -> Explorer handoff

- Из `4. Data Quality` top-level переход в `Silver Reject Explorer` передаёт
  только `$pipeline/$run_type`, но intentionally открывает более широкое окно
  `now-24h` (forensic default) для редких инцидентов и sparse reject events.
- `Top Silver Reject Reasons` и `Top Silver Reject Fields` intentionally не
  дублируют второй dashboard-to-dashboard handoff: оператор использует их как
  bounded cause summary, затем переходит в top-level `Silver Reject Explorer`.
- Оператор SHOULD сначала подтвердить, что текущий spike/аномалия видны в
  summary-панелях DQ (`Top Silver Reject Reasons/Fields`) и только затем делать
  record-level drilldown в Explorer.
- После перехода оператор SHOULD проверить explanatory banner
  `default 24h forensic window`; при шуме или слишком большом объёме данных
  окно можно сузить вручную до operational range.
- Для очень редких инцидентов оператор MAY оставить 24h окно и уточнить
  контекст через `reason_code`, `field`, `run_id` и `payload_hash` перед
  action-операциями в CLI.
- `bioetl-workflow-overview`: dashboard links `0. Control Plane`,
  `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`;
  cross-dashboard handoffs не leaking `$workflow/$status` into non-workflow
  targets.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-workflow-overview`, проверить `Failed Workflow Runs / Range` (`id=2`), `Failed Pipeline Steps / Range` (`id=3`) и `Failed Transform Steps / Range` (`id=6`).
  2. Click #2: перейти в `2. Runtime` для incident triage по pipeline impact, в `4. Data Quality` для transform/filtering fallout, или в `0. Control Plane` для replay/resume trust verification. Prometheus panels use only bounded workflow labels (`workflow`, `status`, `step_kind`) and never require `run_id`/`step_id` labels.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: dashboards с `$pipeline/$run_type` предварительно фильтруют TraceQL по `span."bioetl.pipeline"` и `span."bioetl.run_type"`, а provider dashboard — по `span."bioetl.provider"`. Это не заменяет correlation по `trace_id` / `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом клике.
- `bioetl-runtime` row `Tracing-only Log Hygiene` теперь включает table panel `Alert-to-Action Map` как runbook-lite:
  - `warning_spike` -> вероятная причина: provider instability или DQ threshold drift; следующий шаг: `docs/05-operations/runbooks/dq-failure-investigation.md`.
  - `unstructured_logs_growth` -> вероятная причина: parser/schema drift или не-JSON logger output; следующий шаг: `docs/05-operations/runbooks/incident-response.md` (provider triage).
  - `hygiene_anomaly` -> вероятная причина: runtime-control mismatch/checkpoint lag/stale state; следующий шаг: `docs/05-operations/runbooks/run-manifest-inspection.md`.
  Семантика окна для карты: сигналы читаются в том же active Grafana time range (`$__range`), а trend panel в этом ряду использует `$__interval`; это согласовано с rule-pack потому что condition-summary panels в runtime остаются на `increase(...[$__range])` и не смешивают fixed 30m window с log-hygiene triage.

- Runtime condition-summary triage path:
  `Monitor Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `Inspect DQ Alert Conditions` / `Inspect Freshness Alert Conditions` -> `dq-failure-investigation.md`,
  `Inspect Control-plane Alert Conditions` -> `run-manifest-inspection.md`,
  `Inspect GLOBAL Provider Alert Conditions` -> `incident-response.md`,
  `Monitor No-Records Runs` -> `checkpoint-debugging.md`.

- Known missing runtime panels:
  `Retry vs Failure` и `Batch Size Distribution` не shipped, пока repo не
  подтверждает bounded runtime metric family для этих решений.

## Важные пороги (из JSON)

- `overview.id=214 (System Status)`: `CRITICAL` при runtime blocker `>0`, DQ hard fail `>0`, blocking gold lifecycle или control-plane blocker `>0`; `WARNING` при non-fatal warning-only сигналах; `UNKNOWN` при no recent samples. Next action: follow `overview.id=215`.
- `overview.id=215 (Next Action)`: priority order `Runtime > Control Plane > Gold Lifecycle > DQ > Provider > Workflow > Monitor`. If the selected scope is missing from `bioetl_overview_pipeline_run_type_universe`, the panel falls back to `NO_ROUTE` instead of rendering empty. Next action: open first non-OK surface with same `$pipeline/$run_type`.
- `dq.id=2 (DQ Score Snapshot)`: no-data остается `UNKNOWN`, не `0`; hard-fail signals блокируют promotion, warning-only означает drift. Next action: hard-fail -> reject/quarantine diagnostics; warning-only -> trend + top reasons.
- `dq.id=154 (Blocked Share Trend)`: numerator = `filtered_out + quarantined`,
  denominator = Bronze input in the same window. Sustained growth = filter /
  quarantine pressure, spike = incident. Next action: `Top Silver Reject
  Reasons` + `Silver Reject Explorer`/quarantine CLI.
- `runtime.id=16 (Monitor Runtime Blockers)`: non-zero = active blocker count. Next action: runtime blockers table + culprit stage panels, затем logs/traces при необходимости.
- `runtime.id=220 (Monitor Runtime Error Rate)`: elevated ratio with meaningful Bronze denominator = degradation risk; WARN starts at 5%, dashboard CRIT escalation at 20%. Next action: `Inspect Errors by Stage / Error Code / Range` + failed runs/backlog/lag panels.
- `control-plane.id=907 (Inspect: Control-Plane Telemetry Missing)`: `0=OK`, `1=WARN`, `>=2=CRIT`, `null=UNKNOWN`; non-zero/UNKNOWN means validate scrape/rules before trusting blocker zeros.
- `control-plane.id=130 (Track: Replay / Resume Blockers in Range)`: selected-range blocker count across manifest writes, ledger appends, checkpoint compatibility, replay reconstructability, replay drift, and lineage refs. Любой non-zero value означает investigate before replay/resume, но это historical range evidence, а не first-screen current-status verdict.

- `overview.System Status`: `CRITICAL` при failed runs `>0`, stage backlog `>0`,
  worst lag `>=300s`, DQ hard fail `>0` или control-plane blocker `>0`;
  `WARNING` при warning-сигналах provider/DQ/freshness/workflow или
  pending-gold conditions; `UNKNOWN`
  при отсутствии recent activity/samples; `OK` только при recent activity и
  отсутствии blockers/warnings.
- `overview.Next Action`: runtime имеет приоритет над control-plane,
  blocking gold lifecycle, DQ, provider и workflow; row
  `action_target/action_reason/action_dashboard_uid`
  replaces the old opaque severity-only handoff. `NO_ROUTE` means the selected
  `pipeline/run_type` scope is not present in the overview universe and should
  be validated before deeper drilldown.
- `overview.Gold Lifecycle Current`: table now uses explicit
  `lifecycle_state` rows (`runtime_failed_owner`, `gold_missing_after_success`,
  `pending_no_recent_gold`, `disabled`, `healthy_recent_gold`) instead of a
  single generic gold status number.
- `control-plane.Track: Replay / Resume Blockers in Range`: selected-range blocker
  count. Нулевое значение само по себе не доказывает safety; его нужно читать
  вместе с current trust cards и `Inspect: Control-Plane Telemetry Missing = 0`.
- `control-plane.Inspect: Terminal Run Events by Status in Range`: selected-range
  terminal evidence grouped by `terminal_status`. Эта панель pipeline-scoped only:
  metric contract не несёт `run_type`, поэтому `run_type` selector здесь не
  влияет на breakdown.
- `control-plane.Manifest/Ledger Failure Ratio`: severity projection за
  фиксированное окно `30m`: `0=OK`, `1=WARN` при `>0`, `2=CRIT` при `>0.10`.
- `control-plane.Monitor: GLOBAL Control-Plane Read Failure Ratio`: severity
  projection за фиксированное окно `30m`: `0=OK` при `<=5%`, `1=WARN` при `>5%`,
  `2=CRIT` при `>10%`.
- `control-plane latency p50/p95/p99`: histogram-backed panels сохраняют
  `No data` как diagnostic signal; отсутствие samples не превращается в `0s`.
- `control-plane.Review: Known Missing Replay-Safety Signals`: manifest/run identity,
  config/contract hashes, ledger ordering, checkpoint age vs RPO, replay
  duplicate detection и identity graph completeness документируются как
  отсутствующие evidence surfaces/метрики, а не подменяются fake PromQL.
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


### Runtime dashboard layout note (Detect → Localize → Escalate)

`bioetl-runtime` использует фиксированный triage-order по трём свернутым полосам: `Detect`, `Localize`, `Escalate`.

- **Detect**: быстрый сигнал «есть ли инцидент» (blockers/failed runs/error rate/lag) и первичный выбор направления.
- **Localize**: локализация culprit stage/phase и проверка latency/backlog breakdown.
- **Escalate**: shutdown/terminal-state диагностика и handoff в tracing/log drilldown для подтверждения причины.

На first screen оставлена ровно одна рекомендация drilldown — panel `id=9991` (`First Action`). Оператор сначала читает `Inspect Active Runtime Blocker Detail`, выбирает текущий blocker type, затем идёт по тем же трём полосам в фиксированном порядке.
