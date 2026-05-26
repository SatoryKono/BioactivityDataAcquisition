# Чек-лист проверок для дашбордов BioETL

**Дата**: 2026-05-11  
**Источник**: docs/03-guides/dashboards/*, contracts/*.yaml, grafana/dashboards/*.json  
**Версия**: 1.0.0

---

## Общие проверки (для всех дашбордов)

### Навигация

- [ ] Панель навигации с `id=1000` существует и содержит полную шину
- [ ] Шина включает: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- [ ] Текущий дашборд отображается как disabled dark-gray item
- [ ] После шины включены глобальные adjunct links: `Silver Reject Explorer`, `Explore Logs`, `Explore Traces`
- [ ] Все ссылки открываются в том же окне (`targetBlank: false`)
- [ ] Нет дублирующих dashboard-to-dashboard ссылок в один target
- [ ] Все ссылки используют `includeVars: false`
- [ ] Forensic переменные (`quarantine_run_id`, `payload_hash`) НЕ передаются в non-target dashboards
- [ ] Dashboard links включают `${__url_time_range}`
- [ ] Explore links включают `from=${__from}` и `to=${__to}`
- [ ] Cross-scope ссылки имеют tooltip с явным suffix (`Scope reset: ...` или `Preserves selected scope and time range.`)

### Переменные и селекторы

- [ ] Каждая переменная в `templating.list` имеет непустой `description`
- [ ] Forensic переменные (`quarantine_run_id`, `payload_hash`) отсутствуют в visible selectors для Prometheus dashboards
- [ ] Скрытые переменные justified только для return-path или detail-only scope
- [ ] Скрытые переменные НЕ автоматически становятся visible selectors
- [ ] Нет blanket `includeVars=true` для cross-dashboard navigation
- [ ] Дашборд принадлежит корректному семейству (pipeline_summary, provider_first, workflow_evidence, forensic_explorer)

### Дизайн-система

#### Статусы (для L0 operator dashboards)
- [ ] Статусные панели используют value mapping: `0 → OK` (green), `1 → WARN` (orange), `>=2 → CRIT` (red), `null → UNKNOWN` (gray)
- [ ] `fieldConfig.defaults.color.mode = thresholds`
- [ ] `fieldConfig.defaults.thresholds.mode = absolute`
- [ ] `fieldConfig.defaults.thresholds.steps`: green (null), orange (1), red (2)

#### First-screen current-status stat panels
- [ ] `options.colorMode = background`
- [ ] Explicit value mapping для `0 → OK`, `1 → WARN`, `2 → CRIT`, `null → UNKNOWN`

#### Panel-type visualization standards
- [ ] Current-status stat: `colorMode=thresholds`, `background` для severity cards
- [ ] Selected-range trend stat: `colorMode=value`, `graphMode=area`
- [ ] Selected-range count stat: `colorMode=value`, `graphMode=none`
- [ ] Percentage/score/latency gauge: `showThresholdMarkers=true`, `showThresholdLabels=false` (если не documented exception)
- [ ] Status table column: `custom.cellOptions.type=color-background`
- [ ] Data table: `custom.cellOptions.type=auto` когда default configured
- [ ] Comparitive timeseries: `tooltip.mode=multi`, `tooltip.sort=desc`
- [ ] Scalar trend timeseries: `tooltip.mode=single`, `tooltip.sort=none` или omitted

#### Заголовки панелей
- [ ] Заголовки используют action-first шаблон: `<Action Verb>: <Object/Signal> [<Window>]`
- [ ] Используются глаголы: `Monitor`, `Inspect`, `Track`, `Compare`, `Review`

#### Описания панелей
- [ ] Каждая панель имеет описание
- [ ] Описание содержит: что измеряется (1 предложение)
- [ ] Описание содержит: как интерпретировать `OK/WARN/CRIT/UNKNOWN`
- [ ] Описание содержит: ссылку на runbook/drilldown если применимо

### Layout и структура

#### First-screen responsibility
- [ ] Первый экран отвечает на primary operator question без скролла
- [ ] Current-status/verdict panels НЕ используют `$__range`
- [ ] Range panels включают selected-range wording в title или description
- [ ] Deep details (`run_id`, `payload_hash`, record-level tables) НЕ на first-screen status rows

#### Panel decision matrix
- [ ] Current status / current reason panels: на first screen, fixed current windows, НЕ `$__range`
- [ ] Next action / route panels: на first screen, low-cardinality route/action rules
- [ ] Selected-range count/rate/trend panels: ниже first screen (except compact L0 context), используют `$__range`
- [ ] Raw counter / histogram / latency evidence panels: ниже first screen
- [ ] Forensic row/table/details panels: ниже first screen или в dedicated explorer

#### Visibility tiers
- [ ] Tier 1 (always-visible answer surface): current status, verdict, first action, current causes
- [ ] Tier 2 (always-visible supporting context): KPI context, trust markers, bounded mirrors
- [ ] Tier 3 (below-fold evidence): selected-range evidence
- [ ] Tier 4 (collapsed diagnostics): tracing-only, raw, verbose, rare forensic breakdowns
- [ ] Критический сигнал НЕ живёт исключительно внутри collapsed row

#### GridPos layout
- [ ] Top-level `gridPos` rectangles НЕ overlap
- [ ] Нет unexplained empty row gaps между adjacent bands (если не justified в audit/docs)

#### Collapsed row policy
- [ ] Tracing-only, raw, verbose, или not-required-for-first-pass-triage panels collapsed
- [ ] Collapsed rows имеют descriptive titles по incident scenario

### Данные и метрики

#### No-data/Unknown policy
- [ ] No-data для status panels НЕ silently трактуется как OK
- [ ] `or vector(0)` используется только для true zero-event counters где missing series = zero events
- [ ] Если используется `or vector(0)`, description подтверждает это
- [ ] В остальных случаях no-data остаётся `UNKNOWN`
- [ ] `null` рендерится как `UNKNOWN` с gray color

#### Missing-data semantics by panel class
- [ ] Current-status / current-cause panels: `null` → `UNKNOWN`, `or vector(0)` forbidden
- [ ] Zero-valid event counters: `or vector(0)` только если missing series = zero events
- [ ] Timeseries / latency / histogram evidence: `No data` остаётся diagnostic signal, NOT synthetic healthy value
- [ ] Forensic tables / HTTP-backed explorer: различают valid empty result vs invalid filter chain vs backend failure
- [ ] Trust-marker panels: present только где operator cannot safely interpret first-screen verdict без них

#### Datasource trust semantics
- [ ] Prometheus current-status и current-cause panels remain fail-closed
- [ ] Explicit trust marker добавляется только когда operator could otherwise confuse empty scope, telemetry gap, или backend failure
- [ ] HTTP-backed forensic surfaces различают: valid scope with zero rows vs invalid filter chain vs backend failure

### Units и decimals

- [ ] Event counters: `unit=short`, `decimals=0`
- [ ] Timestamp KPI: `unit=dateTimeAsIso`, `decimals=0`
- [ ] Fractions/percentages: consistent unit внутри dashboard family, consistent `decimals`
- [ ] Схожий KPI в разных dashboards имеет идентичную пару `unit/decimals`

### JSON инварианты

#### Root fields
- [ ] `timezone`: `"browser"`
- [ ] `style`: `"dark"`
- [ ] `editable`: `true`
- [ ] `graphTooltip`: `1`
- [ ] Если `hideControls` присутствует, то `false`

#### Metadata policy
- [ ] L0/L1 dashboards: `time.from=now-12h`, `refresh=30s`
- [ ] L2 forensic (`silver-reject-explorer`): `time.from=now-24h`, `refresh=1m`
- [ ] `schemaVersion` является `30` или `39` (или актуальной версией)
- [ ] Если `iteration` присутствует, то positive integer
- [ ] `tags` включает `bioetl`

### PromQL duplication policy

- [ ] Exact duplicate PromQL либо:
  - [ ] intentionally reused с role-specific justification, OR
  - [ ] consolidated into recording rule или single canonical panel surface
- [ ] Near-duplicate query families panel-local только когда выражают ту же metric family как sibling breakdown
- [ ] Если query family повторяется, есть recording rule или explicit justification

### Actionable links для critical panels

- [ ] Для P1/P2 operator panels (`stat`/`gauge`/`table`): `options.dataLinks` содержит минимум один object
- [ ] Link title начинается с `Open <target>` pattern
- [ ] Link URL ведёт в target dashboard/runbook для drilldown

### Role-based runbook CTA policy

- [ ] Operator/forensic surfaces: critical panels имеют actionable CTA
- [ ] Dashboard-routing-first surface (`overview`): panel-level CTA MAY оставаться dashboard-only
- [ ] Selected-range evidence surface (`workflow-overview`): selected-range evidence counters НЕ требуют panel-level runbook links
- [ ] Если используется runbook link, URL follows canonical GitHub blob pattern
- [ ] Runbook link titles domain-specific, NOT generic `Open Runbook`

---

## 1. bioetl-overview-v2 (L0 Overview)

### Переменные
- [ ] `pipeline` visible, single-select, default `All`
- [ ] `run_type` visible, multi-select with Include All, default `All`
- [ ] Семейство: pipeline_summary
- [ ] Query sources: `prometheus_records_processed_total`

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- [ ] Required top-level links: `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`
- [ ] Panel `214` (System Status) имеет dataLinks: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `215` (First Action) имеет dataLinks: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `9002` (L0 Inputs) имеет dataLinks: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `9003` (Runtime Blockers) имеет dataLink: Open Runtime
- [ ] Panel `9004` (DQ Status) имеет dataLink: Open Data Quality
- [ ] Panel `9005` (Gold Lifecycle) имеет dataLink: Open Runtime
- [ ] Panel `9006` (Control Plane) имеет dataLink: Open Control Plane
- [ ] Panel `9007` (Provider Global) имеет dataLink: Open Provider Health
- [ ] Panel `9008` (Workflow Selected) имеет dataLink: Open Workflow
- [ ] Panel `9013` (Workflow Global) имеет dataLink: Open Workflow

### First-screen структура
- [ ] Tier 1 включает: System Status, First Action, L0 Inputs
- [ ] Tier 2 включает: Runtime Blockers, DQ Status, Gold Lifecycle, Control Plane, Provider Global, Workflow Selected, Workflow Global
- [ ] Tier 3 collapsed: Range Evidence (Historical / Recent History)
- [ ] Tier 4 collapsed: Diagnostics & Docs (Logs / Traces / Raw Metrics)

### KPI ownership
- [ ] System Status canonical для `bioetl-overview-v2`
- [ ] First Action canonical для `bioetl-overview-v2`
- [ ] L0 Inputs canonical для `bioetl-overview-v2`
- [ ] Gold Lifecycle canonical для `bioetl-overview-v2`
- [ ] Provider Global canonical для `bioetl-overview-v2`
- [ ] Workflow Selected canonical для `bioetl-overview-v2`
- [ ] Workflow Global canonical для `bioetl-overview-v2`

### Специфические требования
- [ ] Normalizes `workflow_<pipeline>` back to entity pipeline для current-state queries
- [ ] First-screen answer row без скролла
- [ ] Default entry scope: `Pipeline=All`, `Run Type=All`

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 2. bioetl-control-plane-v1 (0. Control Plane)

### Переменные
- [ ] `pipeline` visible, single-select, default `unknown`
- [ ] `run_type` visible, multi-select with Include All, default `All`
- [ ] Семейство: pipeline_summary
- [ ] Query sources: `prometheus_control_plane_universe`

### Навигация
- [ ] Required top-level links: `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- [ ] Required top-level links: `Silver Reject Explorer`
- [ ] НЕ включает: `Explore Logs`, `Explore Traces`

### First-screen структура
- [ ] Tier 1 включает: Monitor: Replay Safety State, Inspect: Checkpoint Freshness Gap, Monitor: Manifest / Ledger Integrity, Inspect: Telemetry Missing
- [ ] Tier 2 collapsed rows по incident-сценариям (Checkpoint/Replay, Manifest/Ledger, Global Control Plane, Audit/Lineage, Known Missing Signals)
- [ ] Tier 3: selected-range evidence ниже
- [ ] Tier 4 collapsed: diagnostics

### KPI ownership
- [ ] Replay Safety State canonical для `bioetl-control-plane-v1`
- [ ] Checkpoint Freshness Proxy canonical для `bioetl-control-plane-v1`
- [ ] Ledger/Manifest Consistency canonical для `bioetl-control-plane-v1`

### Специфические требования
- [ ] Global lookup/read-path panels в отдельном блоке **Global diagnostics (non-pipeline scoped)**
- [ ] Global diagnostics panels НЕ фильтруются по `$pipeline` / `$run_type`
- [ ] First-screen current-status cards normalize `workflow_<pipeline>` back to entity pipeline
- [ ] Replay/checkpoint panels route к `checkpoint-debugging.md`
- [ ] Manifest/ledger evidence panels route к `run-manifest-inspection.md`
- [ ] Known Blind Spots и terminal-event evidence ниже fold в collapsed incident rows
- [ ] `Identity evidence and remaining replay-safety signals` exposes P0/P1/P2 anchors through `/ops/control-plane/identity-evidence` without Prometheus ID labels
- [ ] `Review: Remaining Replay-Safety Signals` lists only evidence still outside the identity endpoint
- [ ] Starts с answer-first trust cards

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 3. bioetl-runtime (2. Runtime)

### Переменные
- [ ] `pipeline` visible, single-select, default `unknown`
- [ ] `run_type` visible, multi-select with Include All, default `All`
- [ ] `stage` visible, multi-select with Include All
- [ ] Семейство: pipeline_summary
- [ ] Query sources: `prometheus_runtime_pipeline_run_type_universe` (pipeline, run_type), `prometheus_pipeline_stage_expected` (stage)
- [ ] Dependency: `$run_type` зависит от `$pipeline`
- [ ] Dependency: `$stage` зависит от runtime-selected scope

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `1. Overview`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- [ ] Required top-level links: `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### First Action Contract (panel `9991`)
- [ ] Panel `9991` (First Action) существует
- [ ] Min CTA: 4, Max CTA: 4
- [ ] CTA: Review current status
- [ ] CTA: Review range evidence
- [ ] CTA: Inspect top blockers
- [ ] CTA: Inspect active blocker

### First-screen структура
- [ ] Tier 1 включает: First Action, Runtime Status, Runtime Telemetry Gap, Monitor Runtime Blockers, Runtime Blockers
- [ ] `Runtime Status` описан как mirror of shared-shell `Status`, not independent second signal
- [ ] Tier 2 collapsed rows по сценариям: Backlog Trends, Durations, Shutdown Diagnostics, Tracing-only Log Hygiene
- [ ] Tier 3: selected-range evidence ниже
- [ ] Tier 4 collapsed: tracing-only log hygiene

### KPI ownership (mirrors)
- [ ] System Status mirror (canonical: `bioetl-overview-v2`)
- [ ] First Action mirror (canonical: `bioetl-overview-v2`)
- [ ] L0 Inputs mirror (canonical: `bioetl-overview-v2`)
- [ ] Gold Lifecycle mirror (canonical: `bioetl-overview-v2`)
- [ ] Replay Safety State mirror (canonical: `bioetl-control-plane-v1`)
- [ ] Checkpoint Freshness Proxy mirror (canonical: `bioetl-control-plane-v1`)
- [ ] Ledger/Manifest Consistency mirror (canonical: `bioetl-control-plane-v1`)
- [ ] Provider Health mirror (canonical: `bioetl-provider-health-v2`)
- [ ] DQ Status mirror (canonical: `bioetl-dq-v2`)

### Специфические требования
- [ ] Prometheus-first в tracing-off режиме
- [ ] Loki log-hygiene panels в collapsed row `Tracing-only Log Hygiene`
- [ ] Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor `0` to `bioetl_runtime_pipeline_run_type_universe`
- [ ] GLOBAL provider handoff anchors `0` to `bioetl_provider_current_status`
- [ ] Missing scope остаётся `UNKNOWN`, не synthetic OK
- [ ] Unstructured Loki hygiene renders parsed `.__error__`, не template function form
- [ ] Critical panels имеют actionable CTA
- [ ] Normalizes `workflow_<pipeline>` back to entity pipeline для current-triage queries
- [ ] Uses canonical current-status recording rules (`bioetl_runtime_current_status`, `bioetl_runtime_current_blocker_reason`)

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 4. bioetl-provider-health-v2 (3. Provider Health)

### Переменные
- [ ] `provider` visible, single-select, default `unknown`
- [ ] `pipeline_context` hidden context var, default `unknown`
- [ ] `adapter` hidden detail-only, multi-select with Include All
- [ ] Семейство: provider_first
- [ ] Query sources: `prometheus_provider_health_union` (provider), `textbox_navigation_context` (pipeline_context), `prometheus_circuit_breaker_state` (adapter)
- [ ] Dependency: `$pipeline_context` preserved from source
- [ ] Dependency: `$adapter` optional

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `1. Overview`, `2. Runtime`, `4. Data Quality`, `5. Workflow`
- [ ] Required top-level links: `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### First Action Contract (panel `9002`)
- [ ] Panel `9002` (First Action) существует
- [ ] Min CTA: 3, Max CTA: 3
- [ ] CTA: Review severity matrix
- [ ] CTA: Inspect critical providers
- [ ] CTA: Inspect provider top causes

### First-screen структура
- [ ] Tier 1 включает: GLOBAL Provider Scope, Monitor GLOBAL Provider Severity Matrix, Inspect Critical Providers, Inspect Provider Top Causes, First Action
- [ ] Tier 2: provider detail panels и runbook links ниже
- [ ] Tier 3: selected-range evidence
- [ ] Tier 4 collapsed: diagnostics

### KPI ownership
- [ ] Provider Health (aggregated) canonical для `bioetl-provider-health-v2`

### Специфические требования
- [ ] Provider-first dashboard
- [ ] Panel `id=114` остаётся raw source enum (`0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`) ниже first screen
- [ ] `Inspect Provider Top Causes` может быть непустой даже при `GLOBAL severity = OK`
- [ ] Если status non-OK, а canonical cause projection пуста, `Inspect Provider Top Causes` остаётся empty table
- [ ] Переходы из pipeline-scoped dashboards сохраняют `pipeline_context=$pipeline` и fail-close к `provider=unknown`
- [ ] Если source dashboard нет adapter context, `adapter` не передаётся, target использует fallback `All adapters`
- [ ] Critical panels имеют actionable CTA
- [ ] Uses canonical current-status recording rules (`bioetl_provider_current_status`, `bioetl_provider_current_cause`)

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы из `bioetl-provider-health-v2` в `bioetl-workflow-overview` используют маркер `Reset scope`

### Provider context mapping
- [ ] Source dashboards передают `provider_value=unknown`, `adapter_value=unknown` (или `null` для control-plane)

---

## 5. bioetl-dq-v2 (4. Data Quality)

### Переменные
- [ ] `pipeline` visible, single-select, default `unknown`
- [ ] `run_type` visible, multi-select with Include All, default `All`
- [ ] `stage` visible, multi-select with Include All
- [ ] Семейство: pipeline_summary
- [ ] Query sources: `prometheus_records_processed_total`
- [ ] Dependency: `$run_type` зависит от `$pipeline`
- [ ] Dependency: `$stage` зависит от `$pipeline` и `$run_type`

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `5. Workflow`
- [ ] Required top-level links: `Silver Reject Explorer`, `Explore Logs`, `Explore Traces`

### Required panel links
- [ ] Panel `9102` (Inspect DQ Current Reasons) имеет dataLink: Open Silver Reject Explorer

### First Action Contract (panel `9103`)
- [ ] Panel `9103` (Review: First Action) существует
- [ ] Min CTA: 3, Max CTA: 3
- [ ] CTA: Review current status
- [ ] CTA: Inspect current reasons
- [ ] CTA: Open Silver Reject Explorer

### First-screen структура
- [ ] Tier 1 включает: Monitor DQ Current Status, Monitor DQ Threshold State, Inspect DQ Current Reasons, Review: First Action
- [ ] `Monitor DQ Current Status` описан как mirror of shared-shell `Status`, not independent second signal
- [ ] Tier 2 compact current-context band: Monitor: Data Quality Score (Volume-weighted), Monitor: Worst-Entity DQ Score, Monitor: Worst Data Freshness Lag (seconds), Track: Records Quarantined in Range, Track: Soft Threshold Exceeded in Range, Track: Silver Filter Rejects in Range
- [ ] Tier 3: полноширинный Track Range Evidence: Bronze -> Silver -> Gold
- [ ] Tier 4 collapsed rows: Reject / Pareto / Fields, Validation Diagnostics

### KPI ownership
- [ ] DQ Status (Silver Reject / quality posture) canonical для `bioetl-dq-v2`

### Специфические требования
- [ ] Answer-first L2 incident surface
- [ ] First-screen использует canonical current-status recording rules (`bioetl_dq_current_status`, `bioetl_dq_current_reason`)
- [ ] Range evidence, raw tables, Silver reject breakdowns, logs, traces ниже first-screen
- [ ] `Monitor: Data Quality Score (Volume-weighted)` и `Track: Data Quality Score Trend (Volume-weighted)` share expression intentionally
- [ ] `Monitor: Lineage Refs Missing` stays canonical in `bioetl-control-plane-v1`
- [ ] `bioetl-dq-v2` uses a handoff note/link instead of duplicating the metric
- [ ] Critical panels имеют actionable CTA
- [ ] Pipeline-wide 15m snapshot; `$run_type` и stage filters ниже управляют только selected-range evidence

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 6. bioetl-workflow-overview (5. Workflow)

### Переменные
- [ ] `workflow` visible, multi-select with Include All, default `All`
- [ ] `status` visible, multi-select with Include All, default `All`
- [ ] `step_status` visible, multi-select with Include All, default `All`
- [ ] `step_kind` visible, multi-select with Include All, default `All`
- [ ] `pipeline_context` hidden context var, default `unknown`
- [ ] `run_type_context` hidden context var, default `All`
- [ ] `provider_context` hidden context var, default `unknown`
- [ ] Семейство: workflow_evidence
- [ ] Query sources: `prometheus_workflow_runs_total` (workflow, status, context vars), `prometheus_workflow_step_events_total` (step_status, step_kind)
- [ ] Dependency: workflow variables local
- [ ] Dependency: hidden context preserves single-pipeline handoff

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`
- [ ] Required top-level links: `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### Required panel links
- [ ] Panel `9` (First Action) имеет dataLinks: Open 2. Runtime, Open 4. Data Quality, Open 3. Provider Health, Open 0. Control Plane, Open 1. Overview

### First-screen структура
- [ ] Tier 1 включает: Failed Workflow Runs / Range, Failed Pipeline Steps / Range, Failed Transform Steps / Range, Skipped Step Events / Range, Workflow Run Outcomes / Range, First Action
- [ ] Tier 2 collapsed row `Step Diagnostics (collapsed)` с Step Outcomes by Kind / Step Status / Range и Step Duration p95 by Kind / Step Status / Range
- [ ] Tier 3: selected-range evidence
- [ ] Tier 4 collapsed: diagnostics

### KPI ownership (mirrors)
- [ ] Workflow Selected mirror (canonical: `bioetl-overview-v2`)
- [ ] Workflow Global mirror (canonical: `bioetl-overview-v2`)

### Специфические требования
- [ ] Selected-range operational evidence surface
- [ ] НЕ является current-state runtime triage
- [ ] НЕ использует visible `pipeline` / `run_type` selectors
- [ ] Hidden context variables preserve single-pipeline handoff scope
- [ ] Multi-pipeline workflows fail-close к `unknown` / `All` для hidden context vars
- [ ] `First Action` — единственный оправданный panel-level handoff exception
- [ ] Selected-range evidence counters НЕ требуют panel-level runbook links
- [ ] Prometheus panels используют только bounded workflow labels (`workflow`, `status`, `step_status`, `step_kind`)
- [ ] Shipped `First Action` остаётся единственным оправданным dashboard-handoff CTA exception

### Cross-scope markers
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы из всех дашбордов в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 7. bioetl-silver-reject-explorer (Silver Reject Explorer)

### Переменные
- [ ] `pipeline` visible, single-select, required
- [ ] `run_type` visible, multi-select with Include All, default `All`
- [ ] `reason_code` visible, multi-select with Include All, default `All`
- [ ] `field` visible, multi-select with Include All, default `All`
- [ ] `run_id` visible, single-select, empty until selected
- [ ] `payload_hash` visible textbox, empty string
- [ ] Семейство: forensic_explorer
- [ ] Query sources: `prometheus_records_processed_total` (pipeline), `quarantine_filter_options_api` (run_type, reason_code, field, quarantine_run_id backed by `dimension=run_id`), `textbox_forensic_selector` (payload_hash)
- [ ] Dependency: `$pipeline` required before Quarantine Explorer reads
- [ ] Dependency: forensic selectors local only

### Навигация
- [ ] Required top-level links: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- [ ] Required top-level links: `Explore Logs`, `Explore Traces`
- [ ] НЕ включает: self-link to `Silver Reject Explorer`

### First Action Contract (panel `10`)
- [ ] Panel `10` (Review: First Action / No-Data Semantics) существует
- [ ] Min CTA: 2, Max CTA: 2
- [ ] CTA: Review total rejects
- [ ] CTA: Review scoped summary

### First-screen структура
- [ ] Tier 1 включает: Inspect Explorer Scope, Review: First Action / No-Data Semantics, Monitor Filtered Records Total, Track Reject Rate vs Bronze, Inspect Run Scope Summary
- [ ] Tier 2 включает: Inspect Top Reject Reasons, Inspect Top Reject Fields, Inspect Top Reason Signatures
- [ ] Tier 3 включает: Inspect Filtered Records Table, Inspect Selected Record Details
- [ ] Tier 4: forensic details

### Специфические требования
- [ ] API-backed forensic surface
- [ ] Forensic selectors (`quarantine_run_id`, `payload_hash`) НЕ leak в Prometheus dashboards или dashboard-to-dashboard links
- [ ] Default 24h forensic window (explicit explanatory banner)
- [ ] HTTP-backed surface различает: valid empty result vs invalid filter chain vs backend failure
- [ ] First-screen CTA includes bounded row links: Review total rejects, Review scoped summary, Open Data Quality
- [ ] Main table поддерживает dataLinks для self-drilldown по `payload_hash` и CLI handoff
- [ ] CLI handoff links открываются в новой tab (`data:text/plain`)
- [ ] Self-drilldown stays same-tab
- [ ] Requires single-select `$pipeline` потому что quarantine API fail-closed требует явный `pipeline` параметр
- [ ] `Review: First Action / No-Data Semantics` carries bounded CTA row links

### No-data semantics
- [ ] Valid empty result → empty result / no matching rows
- [ ] Unsupported filter chain, empty denominator, invalid scope, backend failure → UNKNOWN/error
- [ ] `unknown` pipeline или `bronze_records=0` → UNKNOWN
- [ ] Zero matching rows → empty-result state
- [ ] Zero-reject workflow run is valid empty explorer state только после подтверждения конкретного pipeline

### Cross-scope markers
- [ ] Переходы из `bioetl-provider-health-v2` используют маркер `Context mapping`
- [ ] Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`

---

## Источники истины

### Машинно-читаемые контракты
- `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- `grafana/dashboards/*.json`

### Человекочитаемые зеркала
- `docs/03-guides/dashboards/README.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/03-guides/dashboards/navigation-contract.md`
- `docs/03-guides/dashboards/design-system.md`
- `docs/03-guides/dashboards/selector-architecture.md`
- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/03-guides/dashboards/dashboard-audit-checklist.md`
- `docs/03-guides/dashboards/panel-title-inventory.md`
- `docs/04-reference/contracts/observability.md`

---

## Автоматизированные проверки

```bash
# Визуальная семантика
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics

# Дубликаты запросов
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates

# Инвентаризация и проверка контрактов
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json

# Тесты навигации
pytest tests/integration/test_grafana_dashboard_links.py

# Тесты селекторов
pytest tests/integration/test_grafana_selector_contract.py

# Тесты переменных
pytest tests/integration/test_grafana_variable_reference.py

# Тесты первого экрана
pytest tests/integration/test_grafana_dashboard_first_screen_contract.py
```

---

## Обновление документации

При изменении поведения дашбордов:
1. Обновить runtime source сначала (`grafana/dashboards/*.json`)
2. Обновить YAML контракты если поведение изменилось
3. Синхронизировать docs mirrors если поведение или contributor guidance изменились
4. Обновить `panel-title-inventory.md` если изменились заголовки панелей
5. Обновить `variable-reference.md` если изменились переменные
6. Обновить `dashboard-v2-usage.md` если изменились navigation/usage patterns
7. Запустить автоматизированные QA проверки
8. Сообщить о выполненных проверках, пропущенных проверках и статусе sync mirrors
