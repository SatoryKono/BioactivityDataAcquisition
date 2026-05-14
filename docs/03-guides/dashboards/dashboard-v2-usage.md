______________________________________________________________________

Version: 1.4.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# BioETL Dashboards v2: Usage

Дата сверки: **2026-05-14**
Источник истины: `grafana/dashboards/*.json`

Machine-readable navigation contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (docs/tests должны соответствовать ему).

Machine-readable selector contract: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`.

V3 baseline planning/reference surfaces:
- `docs/03-guides/dashboards/v3.0/README.md`
- `docs/03-guides/dashboards/v3.0/1-overview.md`

Human-readable selector references:
- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/selector-architecture.md`

## Какие дашборды использовать

| Dashboard                 | UID                             | Для чего                                                                                   |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 0. Control Plane          | `bioetl-control-plane-v1`       | L1/L2 replay/resume safety: manifest, ledger, checkpoint, replay, lineage, global reads    |
| 1. Overview               | `bioetl-overview-v2`            | L0 answer-first dashboard with frozen Overview v3 baseline: explicit scope/provenance header, workflow/run_id context, aggregate-first triage |
| 2. Runtime                | `bioetl-runtime`                | L2 diagnostic runtime triage: blockers, latency, backlog, error localization, handoffs     |
| 3. Provider Health        | `bioetl-provider-health-v2`     | Incident triage по provider health: latency/failures/degraded/retries exhausted            |
| 4. Data Quality           | `bioetl-dq-v2`                  | Качество данных, карантин, аномалии, freshness                                             |
| Silver Reject Explorer    | `bioetl-silver-reject-explorer` | Record-level explorer для `filtered_out`/`FILTERED_OUT_SILVER` записей (quarantine-backed) |
| 5. Workflow               | `bioetl-workflow-overview`      | Selected-range declarative workflow run/step evidence and transform-step latency handoff   |

## From where to enter each dashboard in 1 click

| Target dashboard | 1-click entry source |
| --- | --- |
| `bioetl-control-plane-v1` | canonical navigation bus `0. Control Plane` from every primary dashboard except itself |
| `bioetl-overview-v2` | canonical navigation bus `1. Overview` from every primary dashboard except itself |
| `bioetl-runtime` | canonical navigation bus `2. Runtime` from every primary dashboard except itself |
| `bioetl-provider-health-v2` | canonical navigation bus `3. Provider Health` from every primary dashboard except itself |
| `bioetl-dq-v2` | canonical navigation bus `4. Data Quality` from every primary dashboard except itself |
| `bioetl-workflow-overview` | canonical navigation bus `5. Workflow` from every primary dashboard except itself |
| `bioetl-silver-reject-explorer` | canonical global adjunct link `Silver Reject Explorer` from every shipped dashboard except itself |

## Фильтрация

- `bioetl-overview-v2`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- `bioetl-control-plane-v1`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`
- `bioetl-runtime`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`, `$stage`
- `bioetl-dq-v2`: `$workflow`, `$pipeline`, `$run_type`, `$run_id`, `$stage`
- `bioetl-provider-health-v2`: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`, `$provider`, hidden `$pipeline_context`, `$adapter`
- `bioetl-workflow-overview`: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`, `$status`, `$step_status`, `$step_kind`, hidden
  `$pipeline_context`, `$run_type_context`, `$provider_context`
- `bioetl-silver-reject-explorer`: `$pipeline`, `$run_type`, `$reason_code`, `$field`, `$run_id`, `$payload_hash`
- `bioetl-overview-v2` intentionally ships with `Workflow=All`,
  `Pipeline=All`, `Run Type=All`, and `Run ID=-` как default entry scope.
- Primary dashboards `0..5` now expose the shared context shell
  `$workflow/$pipeline/$run_type/$run_id`. `$workflow` is context/evidence
  unless the panel explicitly documents truthful intersection semantics.
- Во всех non-Overview pipeline/provider dashboards `$pipeline` и `$provider`
  остаются single-select; если исходного контекста нет, используется explicit
  fallback `unknown`.
- `$run_type` всегда имеет include-all fallback; если исходного run-type
  контекста нет, используйте `Run Type=All`, а не `unknown`.
- Переходы в `3. Provider Health` из pipeline-scoped dashboards сохраняют
  `$pipeline_context` для обратного перехода и fail-close'ятся к
  `$provider=unknown`, если source scope не доказывает валидный provider label
  для target dashboard.
- Для `bioetl-silver-reject-explorer` `$pipeline` также остаётся scoped
  single-select, потому что quarantine API fail-closed требует явный
  `pipeline` параметр.
- Переменная `execution` не используется; `$payload_hash` остаётся только в
  `bioetl-silver-reject-explorer`, а `$run_id` в primary dashboards `0..5`
  используется только для local control-plane `ID` panel и не становится
  Prometheus label или cross-dashboard filter.

## Что смотреть в первую очередь

Policy reminder:
- every dashboard still needs one `ONE BIG QUESTION`
- first-screen scope and `First Action` remain mandatory
- provenance/risk context may stay distributed across scope panels, current
  status surfaces, descriptions and linked runbooks

`bioetl-overview-v2` is the canonical frozen Overview v3 baseline. Primary
dashboards `0..5` reuse its visible context shell and common header panels:
`Provenance`, `Status`, `ID`, and `Processed Records`. Current status semantics
still belong to each dashboard role; `workflow` remains evidence context unless
documented otherwise, and `run_id` affects only the local control-plane `ID`
panel.

1. `bioetl-overview-v2`, first screen (no scroll):
   `Provenance`, `Status`, `First Action`, `ID`, and `Processed Records` answer
   the L0 question: what is broken/degraded, what exact control-plane identity
   is selected or resolved, and where to open drilldown first. `OK` requires
   recent activity; missing current evidence remains `UNKNOWN`, not green zero.
1. `bioetl-runtime`, first-screen answer area (без скролла):
   `Provenance`, `Status`, `ID`, `Processed Records`, then
   `Runtime Status`, `Runtime Blockers` и
   `First Action` отвечают на L2 current-cause вопрос и next operator move.
   Compact evidence row содержит `Worst Stage Lag`,
   `Monitor Runtime Blockers`, `Runtime Error Rate`,
   `Runtime Telemetry Gap` и `Failed Runs`; selected-range risk
   markers не определяют current status. Non-zero/UNKNOWN telemetry gap делает
   zero-count cards недоказательными.
   Datasource trust markers are targeted: `Runtime` keeps this explicit
   telemetry-gap panel first-screen, `Control Plane` uses
   `Inspect: Telemetry Missing`, while `Silver Reject Explorer` relies on
   explicit no-data/backend-failure copy instead of a generic datasource-health
   stat tile.
1. `bioetl-runtime`, collapsed row-группы по сценарию:
   `Detect`, `Localize`, `Escalate`, `Tracing-only Log Hygiene`. Открывайте
   ровно одну нужную группу после чтения answer row и selected-range KPI,
   чтобы сократить шум первого экрана.
1. `bioetl-control-plane-v1`, answer row:
   `Provenance`, `Status`, `ID`, `Processed Records`, then
   `Monitor: Replay Safety State`, `Inspect: Checkpoint Freshness Gap`,
   `Monitor: Manifest / Ledger Integrity` и `Inspect: Telemetry Missing`
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
   first screen как evidence. `Inspect Provider Top Causes` может оставаться
   непустой даже при `GLOBAL severity = OK`, потому что canonical cause
   projection включает early-warning provider signals независимо от
   current-status projection; это diagnostic lead, а не самостоятельное
   доказательство current non-OK severity. Если status остаётся non-OK, а
   canonical cause projection пуста, `Inspect Provider Top Causes` остаётся
   empty table; это explainability gap, а не healthy state. В таком случае
   расследование нужно продолжать по severity matrix и optional provider
   diagnostics, а не трактовать пустую таблицу как отсутствие инцидента.
   `First Action` is the bounded CTA surface for this dashboard: review the
   severity matrix, inspect critical providers, or inspect provider top causes
   before leaving the page.
1. `bioetl-dq-v2`, first-screen answer row:
   `Monitor DQ Current Status`, `Monitor DQ Threshold State`,
   `Inspect DQ Current Reasons` и `Review: First Action`
   отвечают на вопрос «DQ сейчас OK/WARN/CRIT/UNKNOWN и какое действие
   первое». Сразу под этим first-screen row расположен compact current-context
   band: `Monitor: Data Quality Score (Volume-weighted)`,
   `Monitor: Worst-Entity DQ Score`, `Monitor: Worst Data Freshness Lag (seconds)`,
   `Track: Records Quarantined in Range`, `Track: Soft Threshold Exceeded in Range`
   и `Track: Silver Filter Rejects in Range`. Полноширинный
   `Track Range Evidence: Bronze -> Silver -> Gold` идёт ниже как
   `Review: First Action` stays the canonical DQ CTA: review current status,
   inspect current reasons, or open `Silver Reject Explorer` without leaking
   unsupported workflow/provider scope.
   selected-range evidence. Это pipeline-wide 15m snapshot; `$run_type` и stage
   filters ниже управляют только selected-range evidence.
1. `bioetl-overview-v2`, routing and evidence rows:
   `Control Plane`, `Runtime`, `Data Quality`, `Provider`,
   `Data Validation`, `Inputs`, и `Workflow` показывают current-only operator
   state с явным scope. Status tables use row-wide threshold coloring, а не
   только окраску ячейки `Status`. Compact historical trend/evidence panels
   вынесены ниже первого экрана в `L1 Historical Trends` и collapsed
   `Range Evidence`; они служат selected-range/L1 evidence и не определяют
   `Status` или `First Action`. `Diagnostics & Docs` содержит routing по
   logs/traces/raw metrics.
1. `bioetl-workflow-overview`, panels `id=2`, `id=3`, `id=6`, `id=7`, `id=4`,
   `id=5`, `id=8`:
   selected-range declarative workflow evidence for failed runs, failed/skipped
   step events, run-outcome mix, step outcomes, и step latency. Используйте его,
   когда нужен bounded workflow evidence layer. Shared `run_id` помогает
   identity lookup в `ID`, но current stage, replay/resume или provider/DQ root
   cause остаются задачами соседних dashboards.

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
│ Provenance                                                      │ Status      │
├──────────────────────┬──────────────┬────────────────────────────────────────┤
│ ID                   │ Processed    │ First Action                           │
│                      │ Records      │                                        │
├──────────────┬───────┬──────────────┬──────────┬─────────────────────────────┤
│ Control Plane│Runtime│ Data Quality │ Provider │ Data Validation             │
├─────────────────────────────────────┬────────────────────────────────────────┤
│ Inputs                              │ Workflow                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾ L1 Historical Trends                                                       │
│ ▾ Range Evidence                                                             │
│ ▾ Diagnostics & Docs                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

Первый экран без скролла должен отвечать на вопрос **«что сломано и куда идти дальше»**:
- что сломано: `Status` + `Inputs` + L1 current cards;
- куда идти дальше: `First Action` с `action_target/action_reason/action_dashboard_uid`;
- какая execution identity выбрана: `ID`, backed by local control-plane manifests;
- что было в окне времени: compact `L1 Historical Trends` и collapsed `Range Evidence`;
- где искать сырые traces/logs/metrics: collapsed `Diagnostics & Docs`.

Compact evidence ниже первого экрана:
- `Runtime Blockers Trend` (`id=9018`): selected-range L1 runtime evidence over
  `bioetl_l1_runtime_blocker_status`; no-data/gaps остаются diagnostic, а не
  OK; handoff `Open Runtime`.
- `DQ Status Trend` (`id=9019`): selected-range L1 Data Quality evidence over
  `bioetl_l1_dq_status`; missing series не доказывает green state; handoff
  `Open Data Quality`.
- `Gold Lifecycle Trend` (`id=9020`): selected-range L1 data-validation
  lifecycle evidence over `bioetl_l1_gold_lifecycle_status` with
  `lifecycle_state`; disabled Gold stage may be OK, but missing series is still
  diagnostic; handoffs `Open Runtime` and `Open Control Plane`.
- `Historical Failures` (`id=9010`): selected-range historical failure table
  over `bioetl_pipeline_runs_total`; zero matching rows only means no failed-run
  samples in the selected range, not current OK; handoff `Open Runtime`.
- `Recent Terminal Runs` (`id=9011`): selected-range non-success terminal-run
  table over `bioetl_pipeline_runs_total`; no terminal rows is not proof of
  current OK; handoffs `Open Control Plane` and `Open Runtime`.

Эти пять panels retained intentionally. Current verdict по-прежнему определяется
только first-screen `Status`, `First Action`, `Inputs` и current L1 cards.
## Silver Filter Rejects workflow

- Для быстрых summary используйте `Silver Rejects + Rate` в
  `bioetl-overview-v2` и `Track: Silver Filter Rejects in Range` в `bioetl-runtime`. Overview
  intentionally не показывает standalone green reject-rate gauge: rate
  интерпретируется только рядом с Bronze denominator / activity context.
- `bioetl-overview-v2` и `bioetl-runtime` содержат явный handoff в
  `4. Data Quality`, но runtime dashboard больше не тащит в себя DQ internals:
  он показывает только compact handoff conditions.
- Для current-state narrowing используйте `Inspect DQ Current Reasons`; для
  bounded cause summary используйте `Inspect: Top Silver Reject Reasons (Pareto)` и
  `Inspect: Top Silver Reject Fields` в collapsed rows `bioetl-dq-v2`.
- Маршрут triage: **L1 summary -> L2 explorer**.
  1. **L1 summary:** начните с `4. Data Quality` (first-screen current status,
     threshold state, reasons, invalid-record-policy note), чтобы определить
     severity и первое действие.
  1. **L1 cause narrowing:** раскройте collapsed rows `Reject / Pareto / Fields` и `Validation Diagnostics`, проверьте `Inspect: Top Silver Reject Reasons (Pareto)` / `Inspect: Top Silver Reject Fields` и связанные diagnostics.
  1. **L2 explorer:** откройте `Silver Reject Explorer` через top-level link в `4. Data Quality` для record-level списка, выбора `reason_code/field/run_id` и detail по `payload_hash`.
  1. **L2 no-data gate:** считайте `0` rejects нормой только когда `Review: First Action / No-Data Semantics` подтверждает конкретный pipeline, доступный Quarantine Explorer и ненулевой Bronze denominator; zero-reject workflow run is a valid empty explorer state only after those checks pass. Zero matching rows остаются empty-result состоянием, а plugin errors, unsupported filter chains, `unknown` pipeline или `bronze_records=0` остаются UNKNOWN/error.
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
`4. Data Quality`, `5. Workflow`. Each page renders the full visual bus in
navigation panel `id=1000`; the current dashboard stays visible as a disabled
dark-gray item, while machine-readable `panel.links` still omit self-links.
The canonical shipped surface is navigation panel `id=1000`, so
`dashboard.links[]` does not need to duplicate the same bus next to Grafana
variables. Any duplicate dashboard-to-dashboard link from one dashboard to the
same target dashboard is forbidden.

Every shipped navigation panel `id=1000` also exposes global adjunct links
`Silver Reject Explorer`, `Explore Logs`, and `Explore Traces` after bus
`0..5`. These navigation-panel links open in the same window, not in a new
tab.
`Explore Logs` is a baseline-first adjunct surface: zero lines can legitimately
mean Loki shipping is disabled, no BioETL streams were shipped in range, or the
operator still needs to refine scope inside Explore.
`Explore Traces` is a traced-run-only adjunct surface; if the runtime used
`NoOpTracing`, empty Tempo results are expected rather than a dashboard defect.
Shipped trace handoff opens the explicit search-first Tempo route, bounds the
initial window to `now-150m..now`, pins a safe default
`groupBy=resource.service.name`, and keeps stable pipeline/provider TraceQL
scope, so Tempo metrics queries stay under the local limit and `All` run-type
selectors do not collapse into an empty regex before the operator changes
grouping.

Variable handoff policy for dashboard links remains strict and bounded:

- `includeVars=false` for every link (no implicit variable leakage).
- Pass only target-scoped variables directly in URL (`var-*`) when required by the destination dashboard.
- For overview/runtime/dq flows pass only `$pipeline/$run_type` unless destination needs another explicit scope.
- For provider flow pass only `$provider/$adapter` (or explicit `All` defaults when opening non-provider dashboards).
- Workflow-specific state variables (`$status`, `$step_status`, `$step_kind`)
  and forensic IDs (`$run_id`, `$payload_hash`) MUST NOT be propagated into
  non-target dashboards. `$workflow` may appear as shared context, but links
  still pass only target-scoped variables explicitly.
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
  dashboards не наследуют unsupported selector leakage. `Status` and
  `First Action` are the first operator answer and both stay in the selected
  `$pipeline/$run_type` scope; subsystem cards preserve explicit drilldown links.

## First 2 clicks scenario (operator)

1. **Click #1:** открыть `bioetl-overview-v2`, прочитать `Status` + `First Action`.
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
  Переход в `3. Provider Health` передаёт `provider=unknown` и
  `pipeline_context=$pipeline`; `adapter` не передаётся, чтобы target dashboard
  использовал собственный fallback `All adapters`.
  First-screen current-status cards normalize a manually selected
  `workflow_<pipeline>` value back to the entity pipeline before reading
  current-state recording rules, so `workflow_chembl_assay` resolves to the
  same trust verdict as `chembl_assay`.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-control-plane-v1`, проверить `Monitor: Replay Safety State` (`id=891`), `Inspect: Telemetry Missing` (`id=907`) и `Next Action: Replay Diagnostics` (`id=906`).
  2. Click #2: перейти через top-level bus в `2. Runtime` (если есть активный blocker) или `4. Data Quality` (если blocker связан с downstream quality symptoms). На первом экране оставлены только current-status Trust KPI: `id=891..893`, `id=907` и единый CTA `id=906`; `Track: Replay / Resume Blockers in Range` (`id=130`) теперь живёт внутри первого collapsed replay/checkpoint row, а `Inspect: Terminal Run Events by Status in Range` (`id=908`) остаётся manifest/ledger range evidence.
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
  mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY` и fail-closed
  `UNKNOWN`, если provider universe существует, а raw status sample отсутствует.
  
  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-provider-health-v2`, проверить `Monitor Current Provider Health Status` (`id=114`) и `Health Check Latency by Provider (p95)` (`id=1`).
  2. Click #2: перейти в `2. Runtime` при active degradation/failure trend или
     в `0. Control Plane` при симптомах retry exhaustion/state inconsistency.
- `bioetl-dq-v2`: dashboard links `0. Control Plane`, `1. Overview`,
  `2. Runtime`, `3. Provider Health`, `5. Workflow`, `Silver Reject Explorer`,
  `Explore Logs`, `Explore Traces` дают переходы для DQ incidents и freshness
  investigation. `Explore Traces` здесь остаётся traced-run-only adjunct;
  включайте tracing через `--tracing` или
  `BIOETL_OBSERVABILITY__TRACING_ENABLED=true`, если ожидаете Tempo evidence.
  Handoff в Explorer передаёт только bounded `$pipeline/$run_type`
  scope, а не generic `includeVars` leakage.
- `bioetl-silver-reject-explorer`: dashboard bus links `0..5` plus global
  adjunct links `Explore Logs` и `Explore Traces`; self-link to
  `Silver Reject Explorer` intentionally omitted. Main table поддерживает data
  links для self-drilldown по `payload_hash` и CLI handoff; self-drilldown
  stays same-tab, while `data:text/plain` CLI links open in a new tab. Верхняя
  explanatory panel явно показывает banner `default 24h forensic window`,
  чтобы оператор не интерпретировал explorer как обычное `now-12h` окно.

### Expected operator behavior for DQ -> Explorer handoff

- Любой pipeline-scoped dashboard handoff в `Silver Reject Explorer` передаёт
  только `$pipeline/$run_type`, а provider/workflow surfaces fail-close'ятся к
  bounded defaults. Explorer intentionally открывает более широкое окно
  `now-24h` (forensic default) для редких инцидентов и sparse reject events.
- `Inspect: Top Silver Reject Reasons (Pareto)` и `Inspect: Top Silver Reject Fields` intentionally не
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
- `bioetl-workflow-overview`: first screen keeps `Failed Workflow Runs / Range`,
  `Failed Pipeline Steps / Range`, `Failed Transform Steps / Range`,
  `Skipped Step Events / Range`, `Workflow Run Outcomes / Range`, and
  `Next Diagnostic Surface`; deeper step evidence now lives under collapsed
  row `Step Diagnostics (collapsed)` with
  `Step Outcomes by Kind / Step Status / Range` and
  `Step Duration p95 by Kind / Step Status / Range`.
- `bioetl-workflow-overview`: `Next Diagnostic Surface` is the only justified
  panel-level handoff exception. Although the header bus already exists, this
  panel remains the sole first-screen workflow CTA and therefore exposes
  bounded `Open ...` dataLinks to neighboring dashboards while preserving the
  time range and resetting unsupported workflow-only state filters.
- `bioetl-silver-reject-explorer`: `Review: First Action / No-Data Semantics`
  now also carries bounded CTA row links (`Review total rejects`,
  `Review scoped summary`, `Open Data Quality`) so the first-screen forensic
  interpretation panel remains actionable without leaking `run_id` or
  `payload_hash` into cross-dashboard handoffs.

  **First 2 clicks (L1):**
  1. Click #1: открыть `bioetl-workflow-overview`, проверить `Failed Workflow Runs / Range` (`id=2`), `Failed Pipeline Steps / Range` (`id=3`) и `Failed Transform Steps / Range` (`id=6`).
  2. Click #2: перейти в `2. Runtime` для incident triage по pipeline impact, в `4. Data Quality` для transform/filtering fallout, или в `0. Control Plane` для replay/resume trust verification. Workflow Prometheus evidence uses bounded workflow labels and never requires `run_id`/`step_id` labels; shared `$pipeline/$run_type/$run_id` context feeds only context/identity surfaces unless a panel documents otherwise.
- Loki drilldown использует безопасный low-cardinality entrypoint `{job="bioetl"}` без dashboard-variable interpolation внутри encoded Explore payload. Это сознательный baseline: Grafana надёжно не подставляет `$pipeline/$provider` в `left=...`, поэтому дополнительное сужение оператор делает уже в самом Explore. Tempo drilldown открывает trace search в том же временном окне; детальная correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.
- Tempo drilldown теперь тоже открывается contextual: pipeline-scoped
  dashboards предварительно фильтруют TraceQL по `span."bioetl.pipeline"`, а
  provider dashboard — по `span."bioetl.provider"`. `run_type` intentionally
  не шиппится в TraceQL handoff, потому что `includeAll` Grafana selector может
  схлопнуться в пустой regex. Это не заменяет correlation по `trace_id` /
  `span_id`, но убирает пустой `{}` и делает handoff полезнее уже на первом
  клике.
- `bioetl-runtime` row `Tracing-only Log Hygiene` содержит Loki-backed panels
  `Inspect Warning Logs`, `Inspect GLOBAL Unstructured Logs`,
  `Inspect Top Warning Events by Message / Range` и
  `Track GLOBAL Log Hygiene Trend`. Это optional tracing-profile evidence, а
  не first-screen status. Log panels используют активный Grafana time range;
  unstructured parser-error panel intentionally renders parsed `.__error__`;
  Prometheus condition-summary panels в runtime используют shipped fixed-window
  recording rules и не зависят от `$__range`.

- Runtime condition-summary triage path:
  `Monitor Pipeline Alert Conditions` -> `pipeline-failure-critical.md`,
  `Inspect DQ Alert Conditions` / `Inspect Freshness Alert Conditions` -> `dq-failure-investigation.md`,
  `Inspect Control-plane Alert Conditions` -> `run-manifest-inspection.md`,
  `Inspect GLOBAL Provider Alert Conditions` -> `incident-response.md`,
  `Monitor No-Records Runs` -> `checkpoint-debugging.md`.
  `0` на этих handoff cards допустим только когда selected runtime
  `pipeline/run_type` universe или GLOBAL provider current-status telemetry
  существует; отсутствующий scope остаётся `UNKNOWN`, а не synthetic OK.

- Known missing runtime panels:
  `Retry vs Failure` и `Batch Size Distribution` не shipped, пока repo не
  подтверждает bounded runtime metric family для этих решений.

## Важные пороги (из JSON)

- `overview.id=214 (Status)`: `CRIT` при runtime blocker `>0`, DQ hard fail `>0`, blocking data-validation lifecycle или control-plane blocker `>0`; `WARN` при non-fatal warning-only сигналах; `UNKNOWN` при no recent samples. Panel links route directly to Runtime / Control Plane / Data Quality / Provider Health / Workflow with the current time range.
- `overview.id=215 (First Action)`: priority order `Runtime > Control Plane > Gold Lifecycle > DQ > Provider > Workflow > Monitor`. If the selected scope is missing from `bioetl_overview_pipeline_run_type_universe` (aliased from the runtime pipeline/run_type universe), the panel falls back to `NO_ROUTE` instead of rendering empty. Next action: open the first non-OK surface via the matching panel link. Runtime / Control Plane / DQ handoffs preserve `$pipeline/$run_type`; Provider Health fail-closes to `provider=unknown` while preserving `pipeline_context`; Workflow accepts the shared context shell but workflow-only state filters are reset.
- `overview` first-screen selected-scope cards normalize a manually selected `workflow_<pipeline>` value back to the entity pipeline before reading `bioetl_l0_*` / `bioetl_l1_*` summary recording rules. For example, `workflow_chembl_assay` resolves to the same current-state summary rows as `chembl_assay`.
- `dq.id=2 (DQ Score Snapshot)`: no-data остается `UNKNOWN`, не `0`; hard-fail signals блокируют promotion, warning-only означает drift. Next action: hard-fail -> reject/quarantine diagnostics; warning-only -> trend + top reasons.
- `overview.id=9002 (Inputs)`: использует `max by (input) (bioetl_l0_input_status_selected{pipeline=~"$pipeline",run_type=~"$run_type"})`. Это compact projected selected-scope surface: first-screen таблица держит одну worst-status строку на operator input, чтобы не требовать scroll на default `Workflow=All/Pipeline=All/Run Type=All`.
- `dq.id=154 (Blocked Share Trend)`: numerator = `filtered_out + quarantined`,
  denominator = Bronze input in the same window. Sustained growth = filter /
  quarantine pressure, spike = incident. Next action: `Top Silver Reject
  Reasons` + `Silver Reject Explorer`/quarantine CLI.
- `runtime.id=16 (Monitor Runtime Blockers)`: non-zero = active blocker count; `UNKNOWN` means missing current runtime status/blocker telemetry and must not be treated as OK. Next action: runtime blockers table + culprit stage panels, затем logs/traces при необходимости.
- `runtime.id=9102 (Runtime Telemetry Gap)`: `0=SCRAPING/RULES OK`, `1=WARN`, `>=2=CRIT`, `null=UNKNOWN`; checks scrape health plus runtime dashboard recording-rule evaluation failures, rule-group presence, and rule-group freshness.
- `runtime.id=205/id=236 (Failed Runs / Monitor No-Records Runs)`: `0` is valid only when `bioetl_runtime_pipeline_run_type_universe` confirms the selected scope; missing selected scope remains `UNKNOWN`.
- `runtime.id=220 (Runtime Error Rate)`: elevated ratio with meaningful 30m Bronze denominator (`>=20`) = degradation risk; WARN starts at 5%, dashboard CRIT escalation at 20%, and lower/missing denominator stays `UNKNOWN`. Next action: `Inspect Errors by Stage / Error Code / Range` + failed runs/backlog/lag panels.
- `runtime` current-triage panels normalize a manually selected `workflow_<pipeline>` value back to the entity pipeline before reading current runtime recording rules and error-rate/lag evidence. For example, `workflow_chembl_assay` resolves to the same current status and blocker scope as `chembl_assay`; `UNKNOWN` on error-rate still remains valid when the 30m Bronze denominator is absent or `<20`.
- `control-plane.id=907 (Inspect: Telemetry Missing)`: `0=OK`, `1=WARN`, `>=2=CRIT`, `null=UNKNOWN`; non-zero/UNKNOWN means validate scrape/rules before trusting blocker zeros.
- `control-plane.id=130 (Track: Replay / Resume Blockers in Range)`: selected-range blocker count across manifest writes, ledger appends, checkpoint compatibility, replay reconstructability, replay drift, and lineage refs. Любой non-zero value означает investigate before replay/resume, но это historical range evidence, а не first-screen current-status verdict.

- `overview.Status`: `CRIT` при failed runs `>0`, stage backlog `>0`,
  worst lag `>=300s`, DQ hard fail `>0` или control-plane blocker `>0`;
  `WARN` при warning-сигналах provider/DQ/freshness/workflow или
  pending-gold conditions; `UNKNOWN`
  при отсутствии recent activity/samples; `OK` только при recent activity и
  отсутствии blockers/warnings. Panel-level links duplicate the canonical
  Runtime / Control Plane / Data Quality / Provider Health / Workflow bus for
  first-click triage.
- `overview.First Action`: runtime имеет приоритет над control-plane,
  blocking gold lifecycle, DQ, provider и workflow; row
  `action_target/action_reason/action_dashboard_uid`
  replaces the old opaque severity-only handoff. `NO_ROUTE` means the selected
  `pipeline/run_type` scope is not present in the overview universe and should
  be validated before deeper drilldown. Panel data links preserve the same
  time range and provide explicit operator handoff even when the next-action route
  itself resolves to `MONITOR`.
- `overview.Data Validation`: first-screen table now aggregates the worst
  current gold lifecycle status by `pipeline` across the selected `run_type`
  scope. Exact `lifecycle_state` detail remains available in Runtime / trend
  surfaces; the Overview card stays compact so it does not require scroll.
- `overview.Workflow`: workflow summary is
  projected from `bioetl_workflow_runs_total` via fixed-window
  `max_over_time(...)` evidence so short-lived successful workflow runs remain
  visible after the CLI process exits. `UNKNOWN` is valid only when the
  selected scope has no recent workflow evidence at all.
- `overview.Recent Terminal Runs`: range-evidence table now
  shows only non-success terminal statuses grouped by `pipeline/status`; success
  completions are intentionally omitted because they create scroll without
  improving first-click triage.
- `control-plane.Track: Replay / Resume Blockers in Range`: selected-range blocker
  count. Нулевое значение само по себе не доказывает safety; его нужно читать
  вместе с current trust cards и `Inspect: Telemetry Missing = 0`.
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
   сначала различите zero matching rows и backend failure. Затем проверьте, что
   выбран конкретный `$pipeline` (не `All`) и что backend отвечает на
   `/ops/quarantine/filter-options?pipeline=<pipeline_name>`.


### Runtime dashboard layout note (Detect → Localize → Escalate)

`bioetl-runtime` использует фиксированный triage-order по трём свернутым полосам: `Detect`, `Localize`, `Escalate`.

- **Detect**: быстрый сигнал «есть ли инцидент» (blockers/failed runs/error rate/lag) и первичный выбор направления.
- **Localize**: локализация culprit stage/phase и проверка latency/backlog breakdown.
- **Escalate**: shutdown/terminal-state диагностика и handoff в tracing/log drilldown для подтверждения причины.

На first screen оставлена ровно одна рекомендация drilldown — panel `id=9991` (`First Action`). Оператор сначала читает current status, top blockers и telemetry gap; `Inspect Active Runtime Blocker Detail` открывается из CTA только когда нужен полный rule-level breakdown внутри `Detect`.
