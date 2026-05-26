# Исчерпывающий список требований к дашбордам BioETL

**Дата**: 2026-05-13  
**Источник**: docs/03-guides/dashboards/*, contracts/*.yaml, grafana/dashboards/*.json  
**Версия**: 1.1.0

---

## Общие требования (ко всем дашбордам)

### Политика-шапка и first-screen preamble

**MUST:**
- Каждый operator dashboard отвечает ровно на один `ONE BIG QUESTION`
- First screen без скролла явно показывает основной вопрос, current scope и
  главный KPI/verdict dashboard family
- First-screen preamble содержит краткий `First action` / `What to do next`
- Provenance и risk context не должны вытеснять главный verdict ниже fold

**Provenance block (MUST для operator dashboards):**
- Источники данных: systems/tables/endpoints или metric families
- Update cadence / schedule
- Transformation/runtime version: `git_commit`, artifact version, pipeline or
  reporter version, либо другой воспроизводимый control-plane reference
- Last successful refresh / latest run timestamp in UTC
- Owner / contact

**Availability / risk block (MUST):**
- SLA / expected freshness window
- Known limitations / lag / partial-scope caveats
- Sensitivity classification (`public`, `internal`, `commercial`, `PII` или
  project-approved equivalent)

**Placement policy:**
- `ONE BIG QUESTION`, scope и `First action` находятся above the fold
- Provenance / availability / risk MAY жить в том же text block или в
  adjacent first-screen context row
- Shipped v2 dashboards MAY удовлетворять этому правилу через комбинацию scope
  panel, current-status row, panel descriptions и monitoring guide references
- New v3 dashboards SHOULD materialize policy header explicitly as a dedicated
  first-screen block

**Источник:** `dashboard-audit-checklist.md`, `01-monitoring-guide.md`

### Навигация

**MUST:**
- Навигационная панель с `id=1000` включает полную шину: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- Текущий дашборд отображается как disabled dark-gray item
- Machine-readable `panel.links` omit self-links (no duplicate navigation)
- После шины `0..5` включены глобальные adjunct links: `Silver Reject Explorer`, `Explore Logs`, `Explore Traces`
- Все ссылки открываются в том же окне (`targetBlank: false`)
- Запрещены дублирующие dashboard-to-dashboard ссылки в один и тот же target dashboard
- Все ссылки используют `includeVars: false`, переменные передаются явно в URL через `var-*`
- Forensic IDs (`quarantine_run_id`, `payload_hash`) НЕ передаются в non-target dashboards
- Cross-scope ссылки имеют tooltip с явным suffix: `Scope reset: ...` или `Preserves selected scope and time range.`
- Time handoff: dashboard links включают `${__url_time_range}`, Explore links включают `from=${__from}`, `to=${__to}`

**Источник:** `contracts/navigation-links.yaml`, `navigation-contract.md`

---

### Переменные и селекторы

**MUST:**
- Каждая переменная в `templating.list` имеет непустой `description`
- Forensic переменные (`quarantine_run_id`, `payload_hash`) НЕ leak в Prometheus dashboards или dashboard-to-dashboard links
- Скрытые переменные justified только для return-path или detail-only scope
- Скрытые переменные НЕ автоматически становятся visible selectors
- Нет blanket `includeVars=true` semantics для cross-dashboard navigation

**Семейства дашбордов:**
- **pipeline_summary**: `bioetl-control-plane-v1`, `bioetl-runtime`, `bioetl-dq-v2`
- **hybrid_overview**: `bioetl-overview-v2` (canonical frozen Overview v3 baseline)
- **provider_first**: `bioetl-provider-health-v2`
- **workflow_evidence**: `bioetl-workflow-overview`
- **forensic_explorer**: `bioetl-silver-reject-explorer`

**Источник:** `contracts/selector-contracts.yaml`, `variable-reference.md`, `selector-architecture.md`

---

### Дизайн-система

**Статусы (MUST для L0 operator dashboards):**
- `0` → `OK` (green)
- `1` → `WARN` (orange)
- `>=2` → `CRIT` (red)
- `null` → `UNKNOWN` (gray)

**Thresholds (MUST для всех status панелей):**
- `fieldConfig.defaults.color.mode = thresholds`
- `fieldConfig.defaults.thresholds.mode = absolute`
- `fieldConfig.defaults.thresholds.steps`: green (null), orange (1), red (2)

**First-screen current-status stat panels (MUST):**
- `options.colorMode = background`
- Explicit value mapping: `0 → OK`, `1 → WARN`, `2 → CRIT`, `null → UNKNOWN`

**Panel-type visualization standards:**
- **Current-status stat**: `colorMode=thresholds`, `background` для designated severity cards, `null → UNKNOWN` mapping где fail-closed
- **Selected-range trend stat**: `colorMode=value`, `graphMode=area`
- **Selected-range count stat**: `colorMode=value`, `graphMode=none`, `or vector(0)` только если missing series = zero events
- **Percentage/score/latency gauge**: `showThresholdMarkers=true`, `showThresholdLabels=false` (unless documented exception)
- **Status table column**: `custom.cellOptions.type=color-background`
- **Data table**: `custom.cellOptions.type=auto` когда default configured
- **Comparative timeseries**: `tooltip.mode=multi`, `tooltip.sort=desc`
- **Scalar trend timeseries**: `tooltip.mode=single`, `tooltip.sort=none` или omitted

**Заголовки панелей (MUST):**
- Action-first шаблон: `<Action Verb>: <Object/Signal> [<Window>]`
- Глаголы: `Monitor`, `Inspect`, `Track`, `Compare`, `Review`
- Примеры: `Monitor: Runtime Failure Rate [24h]`, `Inspect: Provider Retry Saturation [1h]`

**Описание панелей (MUST):**
- Что измеряется (1 предложение)
- Как интерпретировать `OK/WARN/CRIT/UNKNOWN`
- Ссылка на runbook/drilldown если применимо

**Источник:** `design-system.md`

---

### Layout и структура

**First-screen responsibility (MUST):**
- Первый экран отвечает на primary operator question без скролла
- Current-status/verdict panels НЕ используют `$__range`
- Range panels включают selected-range wording в title или description
- Deep details (`run_id`, `payload_hash`, record-level tables) НЕ на first-screen status rows

**Panel decision matrix (MUST):**
- Current status / current reason panels: на first screen, fixed current windows, НЕ `$__range`
- Next action / route panels: на first screen, low-cardinality route/action rules
- Selected-range count/rate/trend panels: ниже first screen (except compact L0 context), MUST использовать `$__range`
- Raw counter / histogram / latency evidence panels: ниже first screen
- Forensic row/table/details panels: ниже first screen или в dedicated explorer

**Layout grammar by dashboard role (MUST):**
- Каждый shipped dashboard отвечает primary operator question перед первым evidence-heavy row
- Historical или selected-range evidence НЕ визуально предшествует current-state answer на L0/L1/L2 dashboards
- Forensic explorer surfaces keep scope semantics и first action выше row-level detail

**Visibility tiers (MUST):**
- **Tier 1** (always-visible answer surface): current status, verdict, first action, current causes
- **Tier 2** (always-visible supporting context): KPI context, trust markers, bounded mirrors
- **Tier 3** (below-fold evidence): selected-range evidence
- **Tier 4** (collapsed diagnostics): tracing-only, raw, verbose, rare forensic breakdowns
- Критический сигнал НЕ живёт исключительно внутри collapsed row

**GridPos layout (MUST):**
- Top-level `gridPos` rectangles НЕ overlap
- Navigation, scope, first-action, current-status, range evidence, collapsed rows занимают explicit non-overlapping bands
- Нет unexplained empty row gaps между adjacent bands (unless justified in audit/docs)

**Collapsed row policy (MUST):**
- Tracing-only, raw, verbose, или not-required-for-first-pass-triage panels collapsed
- Collapsed rows имеют descriptive titles по incident scenario (например, `Incident Drilldown: ...`)

**Источник:** `design-system.md`, `dashboard-audit-checklist.md`

---

### Данные и метрики

**No-data/Unknown policy (MUST):**
- Нет silent treatment of no-data как OK для status panels
- Если no-data действительно равно zero events, query использует explicit `... or vector(0)` и description подтверждает это
- Во всех остальных случаях no-data остаётся `UNKNOWN`
- `null` рендерится как `UNKNOWN` с gray color
- `or vector(0)` используется только для true zero-event counters где missing series семантически означает zero events

**Missing-data semantics by panel class (MUST):**
- **Current-status / current-cause panels**: `null` → `UNKNOWN`, `or vector(0)` forbidden
- **Zero-valid event counters**: `or vector(0)` allowed только если missing series = zero events, visible в query или description
- **Timeseries / latency / histogram evidence**: `No data` остаётся diagnostic signal, NOT synthetic healthy value
- **Forensic tables / HTTP-backed explorer**: различать valid empty result vs unsupported filter chain vs backend failure
- **Trust-marker panels**: present только где operator cannot safely interpret first-screen verdict без них

**Datasource trust semantics (MUST):**
- Prometheus current-status и current-cause panels remain fail-closed (preserve `UNKNOWN`, no `or vector(0)`)
- `or vector(0)` valid только для true zero-event counters
- Explicit trust marker добавляется только когда operator could otherwise confuse empty scope, telemetry gap, или backend failure
- HTTP-backed forensic surfaces MUST различать: valid scope with zero rows vs invalid filter chain vs backend failure

**Источник:** `design-system.md`, `dashboard-audit-checklist.md`

---

### Units и decimals (MUST)

- Event counters (`... Missing`, `... Incompatibilities`, `... Failures`): `unit=short`, `decimals=0`
- Timestamp KPI (`Latest Successful Data Timestamp`): `unit=dateTimeAsIso`, `decimals=0`
- Fractions/percentages (`... Rate`, `... Ratio`): consistent unit внутри dashboard family (`percentunit` или `percent`), consistent `decimals` (обычно `0` или `2`)
- Схожий KPI в разных dashboards имеет идентичную пару `unit/decimals`

**Источник:** `design-system.md`

---

### JSON инварианты (MUST)

**Root fields:**
- `timezone`: `"browser"`
- `style`: `"dark"`
- `editable`: `true`
- `graphTooltip`: `1`
- `hideControls`: если присутствует, MUST быть `false`

**Metadata policy:**
- L0/L1 dashboards: `time.from=now-12h`, `refresh=30s`
- L2 forensic (`silver-reject-explorer`): `time.from=now-24h`, `refresh=1m`
- `schemaVersion` MAY remain `30` или `39` до explicit Grafana migration decision
- `iteration`: если присутствует, MUST быть positive integer
- `tags`: MUST include `bioetl`, MAY include role/domain tags

**Export noise (NOT correctness failure):**
- Mixed panel-level `pluginVersion` values NOT treated как standalone correctness failure
- Нет bulk-rewrite shipped dashboard JSON только чтобы force один `pluginVersion` без proven regression

**Источник:** `design-system.md`, `contracts/navigation-links.yaml`

---

### PromQL duplication policy (MUST)

**Normative rules:**
- Exact duplicate PromQL across more than one panel MUST быть либо:
  - intentionally reused с role-specific justification, OR
  - consolidated into recording rule или single canonical panel surface
- Near-duplicate query families SHOULD оставаться panel-local только когда они выражают ту же metric family как sibling breakdown
- Если тот же query family повторяется across multiple panels/dashboards, priority:
  1. Recording rule / shared canonical metric
  2. Explicit justification в dashboard audit/tests
  3. Raw duplication только как temporary exception

**Audited exact-duplicate reuse:**
- `Monitor: Data Quality Score (Volume-weighted)` и `Track: Data Quality Score Trend (Volume-weighted)` в `bioetl-dq-v2` share expression intentionally
- `Monitor: Lineage Refs Missing` canonically belongs to `bioetl-control-plane-v1`
- `bioetl-dq-v2` uses a textual handoff instead of duplicating the same counter

**Источник:** `design-system.md`, `dashboard-audit-checklist.md`

---

### Actionable links для critical panels (MUST)

Для P1/P2 operator panels (`stat`/`gauge`/`table`):
- `options.dataLinks` содержит минимум один object
- `title` начинается с `Open <target>` pattern
- `url` ведёт в target dashboard/runbook для drilldown

**Источник:** `design-system.md`

---

### Role-based runbook CTA policy (MUST)

- Operator/forensic surfaces (`runtime`, `control-plane`, `provider-health`, `dq`, `silver-reject-explorer`): critical panels SHOULD иметь actionable CTA
- Dashboard-routing-first surface (`overview`): panel-level CTA MAY оставаться dashboard-only
- Selected-range evidence surface (`workflow-overview`): selected-range evidence counters НЕ требуют panel-level runbook links
- Если используется runbook link, URL follows canonical GitHub blob pattern: `https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/<name>.md`
- Runbook link titles остаются domain-specific, NOT generic `Open Runbook`

**Источник:** `design-system.md`

---

## 1. bioetl-overview-v2 (L0 Overview)

### Назначение
Canonical L0 answer-first hub using the frozen `1. Overview v3` layout as the baseline: отвечает на вопрос "что сейчас broken/degraded и куда drill down первым" с явным provenance/scope header и локальной identity context.

### Переменные
- **Видимые**: `workflow` (single-select with Include All, default `All`), `pipeline` (single-select with Include All, default `All`), `run_type` (multi-select with Include All, default `All`), `run_id` (single-select, default `-`)
- **Семейство**: hybrid_overview
- **Query sources**: `bioetl_workflow_runs_total`, `bioetl_records_processed_total`, local control-plane `/ops/control-plane/filter-options?dimension=run_id&response_shape=list`
- **Run ID semantics**: `run_id` is preserved between primary dashboards for HTTP `ID`/details panels and MUST NOT appear in Prometheus queries or generic Silver Explorer links.

### Навигация (required_top_level_links)
- `0. Control Plane`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### Required panel links (dataLinks)
- Panel `214` (Status) → Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- Panel `215` (First Action) → Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- Panel `9002` (Inputs) → Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- Panel `9003` (Runtime) → Open Runtime
- Panel `9004` (Data Quality) → Open Data Quality
- Panel `9005` (Data Validation) → Open Runtime
- Panel `9006` (Control Plane) → Open Control Plane
- Panel `9007` (Provider) → Open Provider Health
- Panel `9013` (Workflow) → Open Workflow

### First-screen структура
- **Tier 1**: `Provenance`, `Status`, `First Action`, `ID`, `Processed Records`
- **Tier 2**: `Control Plane`, `Runtime`, `Data Quality`, `Provider`, `Data Validation`, `Inputs`, `Workflow`
- **Tier 3**: collapsed `L1 Historical Trends`, collapsed `Range Evidence`
- **Tier 4**: collapsed `Diagnostics & Docs`

### KPI ownership (canonical)
- Status → canonical for `bioetl-overview-v2`, mirrors: `2. Runtime`, `0. Control Plane`, `5. Workflow`
- First Action → canonical for `bioetl-overview-v2`, mirrors: `2. Runtime`, `3. Provider Health`
- Inputs → canonical for `bioetl-overview-v2`, mirrors: `2. Runtime`, `4. Data Quality`, `0. Control Plane`
- Data Validation → canonical for `bioetl-overview-v2`, mirrors: `2. Runtime`, `0. Control Plane`
- Provider → canonical for `bioetl-overview-v2`, mirrors: `3. Provider Health`
- Workflow → canonical for `bioetl-overview-v2`, mirrors: `5. Workflow`

### Специфические требования
- Normalizes `workflow_<pipeline>` back to entity pipeline для current-state queries
- `workflow` is visible evidence context; current-status PromQL remains pipeline/run_type scoped until truthful intersection semantics exist.
- `run_id` resolves optional control-plane identity only in `ID`; aggregate `Pipeline=All` scope MUST NOT claim one manifest identity unless exact `run_id` is selected.
- First-screen answer surface follows the frozen Overview v3 layout.
- Panel-level CTA MAY оставаться dashboard-only (не требует прямых runbook links)
- Intentionally ships с `Workflow=All`, `Pipeline=All`, `Run Type=All`, `Run ID=-` как default entry scope

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 2. bioetl-control-plane-v1 (0. Control Plane)

### Назначение
L1/L2 replay/resume safety: manifest, ledger, checkpoint, replay, lineage, global reads

### Переменные
- **Видимые**: `pipeline` (single-select, default `unknown`), `run_type` (multi-select with Include All, default `All`)
- **Семейство**: pipeline_summary
- **Query sources**: `prometheus_control_plane_universe`

### Навигация (required_top_level_links)
- `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- `Silver Reject Explorer`
- **НЕ включает**: `Explore Logs`, `Explore Traces`

### Required panel links
- Нет обязательных panel-level dataLinks в контракте

### First-screen структура
- **Tier 1**: `Monitor: Replay Safety State`, `Inspect: Checkpoint Freshness Gap`, `Monitor: Manifest / Ledger Integrity`, `Inspect: Telemetry Missing`
- **Tier 2**: collapsed rows по incident-сценариям (Checkpoint/Replay, Manifest/Ledger, Global Control Plane, Audit/Lineage, Known Missing Signals)
- **Tier 3**: selected-range evidence ниже
- **Tier 4**: collapsed diagnostics

### KPI ownership (canonical)
- Replay Safety State → canonical for `bioetl-control-plane-v1`, mirrors: `1. Overview`, `2. Runtime`
- Checkpoint Freshness Proxy → canonical for `bioetl-control-plane-v1`, mirrors: `2. Runtime`
- Ledger/Manifest Consistency → canonical for `bioetl-control-plane-v1`, mirrors: `2. Runtime`

### Специфические требования
- Global lookup/read-path panels в отдельном блоке **Global diagnostics (non-pipeline scoped)**, НЕ фильтруются по `$pipeline` / `$run_type`
- First-screen current-status cards normalize `workflow_<pipeline>` back to entity pipeline
- Replay/checkpoint panels route к `checkpoint-debugging.md`
- Manifest/ledger evidence panels route к `run-manifest-inspection.md`
- Known Blind Spots и terminal-event evidence ниже fold в collapsed incident rows, не в first-screen trust block
- `Identity evidence and remaining replay-safety signals` ниже fold использует `/ops/control-plane/identity-evidence` для overview/P1/P2 anchors, typed source/drilldown metadata, identity gaps, checkpoint compare и copy-friendly full values; remaining replay-safety note перечисляет только сигналы вне этого endpoint.
- Starts с answer-first trust cards: replay safety state, checkpoint freshness gap, ledger/manifest consistency, telemetry presence

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 3. bioetl-runtime (2. Runtime)

### Назначение
L2 diagnostic runtime triage: blockers, latency, backlog, error localization, handoffs

### Переменные
- **Видимые**: `pipeline` (single-select, default `unknown`), `run_type` (multi-select with Include All, default `All`), `stage` (multi-select with Include All)
- **Семейство**: pipeline_summary
- **Query sources**: `prometheus_runtime_pipeline_run_type_universe` (pipeline, run_type), `prometheus_pipeline_stage_expected` (stage)
- **Dependency chains**: `$run_type` зависит от `$pipeline`, `$stage` зависит от runtime-selected scope

### Навигация (required_top_level_links)
- `0. Control Plane`, `1. Overview`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### First Action Contract (panel `9991`)
- **Min CTA**: 4, **Max CTA**: 4
- **CTAs**: Review current status, Review range evidence, Inspect top blockers, Inspect active blocker

### First-screen структура
- **Tier 1**: `First Action`, `Runtime Status`, `Runtime Telemetry Gap`, `Monitor Runtime Blockers`, `Runtime Blockers`
- `Runtime Status` is an expanded mirror of compact shared-shell `Status`, not an independent second current-status signal.
- **Tier 2**: collapsed rows по сценариям: `Backlog Trends`, `Durations`, `Shutdown Diagnostics`, `Tracing-only Log Hygiene`
- **Tier 3**: selected-range evidence ниже
- **Tier 4**: collapsed tracing-only log hygiene

### KPI ownership (canonical mirrors)
- Status → mirror (canonical: `bioetl-overview-v2`)
- First Action → mirror (canonical: `bioetl-overview-v2`)
- Inputs → mirror (canonical: `bioetl-overview-v2`)
- Data Validation → mirror (canonical: `bioetl-overview-v2`)
- Replay Safety State → mirror (canonical: `bioetl-control-plane-v1`)
- Checkpoint Freshness Proxy → mirror (canonical: `bioetl-control-plane-v1`)
- Ledger/Manifest Consistency → mirror (canonical: `bioetl-control-plane-v1`)
- Provider Health → mirror (canonical: `bioetl-provider-health-v2`)
- DQ Status → mirror (canonical: `bioetl-dq-v2`)

### Специфические требования
- Prometheus-first в tracing-off режиме
- Loki log-hygiene panels в collapsed row `Tracing-only Log Hygiene`
- Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor `0` to `bioetl_runtime_pipeline_run_type_universe`
- GLOBAL provider handoff anchors `0` to `bioetl_provider_current_status`
- Missing scope остаётся `UNKNOWN`, не synthetic OK
- Unstructured Loki hygiene renders parsed `.__error__`, не template function form
- Critical panels SHOULD иметь actionable CTA с runbook/dashboard links
- Normalizes `workflow_<pipeline>` back to entity pipeline для current-triage queries
- Uses canonical current-status recording rules (`bioetl_runtime_current_status`, `bioetl_runtime_current_blocker_reason`)

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 4. bioetl-provider-health-v2 (3. Provider Health)

### Назначение
Incident triage по provider health: latency/failures/degraded/retries exhausted

### Переменные
- **Видимые**: `provider` (single-select, default `unknown`)
- **Скрытые контекстные**: `pipeline_context` (hidden context var, default `unknown`)
- **Скрытые detail-only**: `adapter` (multi-select with Include All)
- **Семейство**: provider_first
- **Query sources**: `prometheus_provider_health_union` (provider), `textbox_navigation_context` (pipeline_context), `prometheus_circuit_breaker_state` (adapter)
- **Dependency chains**: `$pipeline_context` preserved from source, `$adapter` optional

### Навигация (required_top_level_links)
- `0. Control Plane`, `1. Overview`, `2. Runtime`, `4. Data Quality`, `5. Workflow`
- `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### First Action Contract (panel `9002`)
- **Min CTA**: 3, **Max CTA**: 3
- **CTAs**: Review severity matrix, Inspect critical providers, Inspect provider top causes

### First-screen структура
- **Tier 1**: `GLOBAL Provider Scope`, `Monitor GLOBAL Provider Severity Matrix`, `Inspect Critical Providers`, `Inspect Provider Top Causes`, `Monitor Provider Telemetry Freshness`, `First Action`
- **Tier 2**: provider detail panels и runbook links ниже
- **Tier 3**: selected-range evidence
- **Tier 4**: collapsed diagnostics

### KPI ownership (canonical)
- Provider Health (aggregated) → canonical for `bioetl-provider-health-v2`, mirrors: `1. Overview`, `2. Runtime`

### Специфические требования
- Provider-first dashboard
- Panel `id=114` остаётся raw source enum (`0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`) ниже first screen как evidence
- Panel `id=9104` остаётся first-screen trust marker for `bioetl_provider_current_status` freshness; missing 15m samples mean telemetry gap, not healthy provider state
- `Inspect Provider Top Causes` может быть непустой даже при `GLOBAL severity = OK` (early-warning provider signals независимо от current-status projection)
- Если status остаётся non-OK, а canonical cause projection пуста, `Inspect Provider Top Causes` остаётся empty table (explainability gap, не healthy state)
- Переходы из pipeline-scoped dashboards сохраняют `pipeline_context=$pipeline` и fail-close к `provider=unknown`
- Если source dashboard нет adapter context, `adapter` не передаётся, target использует собственный fallback `All adapters`
- Critical panels SHOULD иметь actionable CTA
- Uses canonical current-status recording rules (`bioetl_provider_current_status`, `bioetl_provider_current_cause`)

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы из `bioetl-provider-health-v2` в `bioetl-workflow-overview` используют маркер `Reset scope`

### Provider context mapping contract
- Source dashboards передают `provider_value=unknown`, `adapter_value=unknown` (или `null` для control-plane)

---

## 5. bioetl-dq-v2 (4. Data Quality)

### Назначение
Качество данных, карантин, аномалии, freshness

### Переменные
- **Видимые**: `pipeline` (single-select, default `unknown`), `run_type` (multi-select with Include All, default `All`), `stage` (multi-select with Include All)
- **Семейство**: pipeline_summary
- **Query sources**: `prometheus_records_processed_total`
- **Dependency chains**: `$run_type` зависит от `$pipeline`, `$stage` зависит от `$pipeline` и `$run_type`

### Навигация (required_top_level_links)
- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `5. Workflow`
- `Silver Reject Explorer`, `Explore Logs`, `Explore Traces`

### Required panel links
- Panel `9102` (Inspect DQ Current Reasons) → Open Silver Reject Explorer

### First Action Contract (panel `9103`)
- **Min CTA**: 3, **Max CTA**: 3
- **CTAs**: Review current status, Inspect current reasons, Open Silver Reject Explorer

### First-screen структура
- **Tier 1**: `Monitor DQ Current Status`, `Monitor DQ Threshold State`, `Inspect DQ Current Reasons`, `Review: First Action`
- `Monitor DQ Current Status` is an expanded mirror of compact shared-shell `Status`, not an independent second current-status signal.
- **Tier 2**: compact current-context band: `Monitor: Data Quality Score (Volume-weighted)`, `Monitor: Worst-Entity DQ Score`, `Monitor: Worst Data Freshness Lag (seconds)`, `Track: Records Quarantined in Range`, `Track: Soft Threshold Exceeded in Range`, `Track: Silver Filter Rejects in Range`
- **Tier 3**: полноширинный `Track Range Evidence: Bronze -> Silver -> Gold`
- **Tier 4**: collapsed rows: `Reject / Pareto / Fields`, `Validation Diagnostics`

### KPI ownership (canonical)
- DQ Status (Silver Reject / quality posture) → canonical for `bioetl-dq-v2`, mirrors: `1. Overview`, `2. Runtime`

### Специфические требования
- Answer-first L2 incident surface
- First-screen использует canonical current-status recording rules (`bioetl_dq_current_status`, `bioetl_dq_current_reason`)
- Range evidence, raw tables, Silver reject breakdowns, logs, traces ниже first-screen
- `Monitor: Data Quality Score (Volume-weighted)` и `Track: Data Quality Score Trend (Volume-weighted)` share expression intentionally (different UI roles)
- `Monitor: Lineage Refs Missing` canonically belongs to `bioetl-control-plane-v1`
- `bioetl-dq-v2` uses a textual handoff instead of duplicating the same counter
- Critical panels SHOULD иметь actionable CTA
- Pipeline-wide 15m snapshot; `$run_type` и stage filters ниже управляют только selected-range evidence

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 6. bioetl-workflow-overview (5. Workflow)

### Назначение
Selected-range declarative workflow run/step evidence and transform-step latency handoff

### Переменные
- **Видимые**: `workflow` (multi-select with Include All, default `All`), `status` (multi-select with Include All, default `All`), `step_status` (multi-select with Include All, default `All`), `step_kind` (multi-select with Include All, default `All`)
- **Скрытые контекстные**: `pipeline_context` (hidden context var, default `unknown`), `run_type_context` (hidden context var, default `All`), `provider_context` (hidden context var, default `unknown`)
- **Семейство**: workflow_evidence
- **Query sources**: `prometheus_workflow_runs_total` (workflow, status, context vars), `prometheus_workflow_step_events_total` (step_status, step_kind)
- **Dependency chains**: workflow variables local, hidden context preserves single-pipeline handoff

### Навигация (required_top_level_links)
- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`
- `Explore Logs`, `Explore Traces`, `Silver Reject Explorer`

### Required panel links
- Panel `9` (First Action) → Open 2. Runtime, Open 4. Data Quality, Open 3. Provider Health, Open 0. Control Plane, Open 1. Overview

### First-screen структура
- **Tier 1**: `Failed Workflow Runs / Range`, `Failed Pipeline Steps / Range`, `Failed Transform Steps / Range`, `Skipped Step Events / Range`, `Workflow Run Outcomes / Range`, `First Action`
- **Tier 2**: collapsed row `Step Diagnostics (collapsed)` с `Step Outcomes by Kind / Step Status / Range` и `Step Duration p95 by Kind / Step Status / Range`
- **Tier 3**: selected-range evidence
- **Tier 4**: collapsed diagnostics

### KPI ownership (canonical mirrors)
- Workflow → canonical for `bioetl-overview-v2`

### Специфические требования
- Selected-range operational evidence surface
- НЕ является current-state runtime triage
- НЕ использует visible `pipeline` / `run_type` selectors
- Hidden context variables preserve single-pipeline handoff scope
- Multi-pipeline workflows fail-close к `unknown` / `All` для hidden context vars
- `First Action` — единственный оправданный panel-level handoff exception
- Selected-range evidence counters НЕ требуют panel-level runbook links
- Prometheus panels используют только bounded workflow labels (`workflow`, `status`, `step_status`, `step_kind`), не требуют `run_id`/`step_id` labels
- Shipped `First Action` остаётся единственным оправданным dashboard-handoff CTA exception

### Cross-scope marker contract
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы из всех дашбордов в `bioetl-workflow-overview` используют маркер `Reset scope`

---

## 7. bioetl-silver-reject-explorer (Silver Reject Explorer)

### Назначение
Record-level explorer для `filtered_out`/`FILTERED_OUT_SILVER` записей (quarantine-backed)

### Переменные
- **Видимые**: `pipeline` (single-select, required), `run_type` (multi-select with Include All, default `All`), `reason_code` (multi-select with Include All, default `All`), `field` (multi-select with Include All, default `All`), `quarantine_run_id` (single-select, empty until selected; backend `dimension=run_id`), `payload_hash` (visible textbox, empty string)
- **Семейство**: forensic_explorer
- **Query sources**: `prometheus_records_processed_total` (pipeline), `quarantine_filter_options_api` (run_type, reason_code, field, quarantine_run_id backed by `dimension=run_id`), `textbox_forensic_selector` (payload_hash)
- **Dependency chains**: `$pipeline` required before Quarantine Explorer reads, forensic selectors local only

### Навигация (required_top_level_links)
- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`
- `Explore Logs`, `Explore Traces`
- **НЕ включает**: self-link to `Silver Reject Explorer`

### First Action Contract (panel `10`)
- **Min CTA**: 2, **Max CTA**: 2
- **CTAs**: Review total rejects, Review scoped summary

### First-screen структура
- **Tier 1**: `Inspect Explorer Scope`, `Monitor Explorer Backend Health`, `Review: First Action / No-Data Semantics`, `Monitor Filtered Records Total`, `Track Reject Rate vs Bronze`, `Inspect Run Scope Summary`
- **Tier 2**: `Inspect Top Reject Reasons`, `Inspect Top Reject Fields`, `Inspect Top Reason Signatures`
- **Tier 3**: `Inspect Filtered Records Table`, `Inspect Selected Record Details`
- **Tier 4**: forensic details

### Специфические требования
- API-backed forensic surface
- Forensic selectors (`quarantine_run_id`, `payload_hash`) НЕ leak в Prometheus dashboards или dashboard-to-dashboard links
- Default 24h forensic window (explicit explanatory banner)
- HTTP-backed surface MUST различать: valid empty result vs invalid filter chain vs backend failure
- `Monitor Explorer Backend Health` MUST read `/health/live` through `Quarantine Explorer` and act as first-screen backend trust marker before empty tables are treated as evidence
- First-screen CTA includes bounded row links: `Review total rejects`, `Review scoped summary`, `Open Data Quality`
- Main table поддерживает dataLinks для self-drilldown по `payload_hash` и CLI handoff
- CLI handoff links открываются в новой tab (`data:text/plain`)
- Self-drilldown stays same-tab
- Requires single-select `$pipeline` потому что quarantine API fail-closed требует явный `pipeline` параметр
- `Review: First Action / No-Data Semantics` carries bounded CTA row links

### No-data semantics
- Valid empty result → empty result / no matching rows
- Unsupported filter chain, empty denominator, invalid scope, backend failure → UNKNOWN/error
- `unknown` pipeline или `bronze_records=0` → UNKNOWN
- Zero matching rows → empty-result state
- Zero-reject workflow run is valid empty explorer state только после подтверждения конкретного pipeline, доступного Quarantine Explorer и ненулевого Bronze denominator

### Cross-scope marker contract
- Переходы из `bioetl-provider-health-v2` используют маркер `Context mapping`
- Переходы в `bioetl-provider-health-v2` используют маркер `Context mapping`

---

## Источники истины

### Машинно-читаемые контракты
- `docs/03-guides/dashboards/contracts/navigation-links.yaml` — навигация, ссылки, время, KPI ownership, cross-scope markers, first action contract
- `docs/03-guides/dashboards/contracts/selector-contracts.yaml` — селекторы, переменные, семейства дашбордов, hidden handoff contract
- `grafana/dashboards/*.json` — фактические JSON дашбордов

### Человекочитаемые зеркала
- `docs/03-guides/dashboards/README.md` — индекс дашбордов, KPI ownership
- `docs/03-guides/dashboards/monitoring-index.md` — индекс для операторов при инцидентах
- `docs/03-guides/dashboards/navigation-contract.md` — контракт навигации
- `docs/03-guides/dashboards/design-system.md` — дизайн-система
- `docs/03-guides/dashboards/selector-architecture.md` — архитектура селекторов
- `docs/03-guides/dashboards/variable-reference.md` — справочник переменных
- `docs/03-guides/dashboards/dashboard-v2-usage.md` — использование дашбордов
- `docs/03-guides/dashboards/dashboard-audit-checklist.md` — исчерпывающий чек-лист
- `docs/03-guides/dashboards/panel-title-inventory.md` — инвентарь заголовков панелей
- `docs/04-reference/contracts/observability.md` — спецификация наблюдаемости

---

## Автоматизированные проверки

Для проверки compliance:
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
2. Обновить YAML контракты если поведение изменилось (`navigation-links.yaml`, `selector-contracts.yaml`)
3. Синхронизировать docs mirrors если поведение или contributor guidance изменились
4. Обновить `panel-title-inventory.md` если изменились заголовки панелей
5. Обновить `variable-reference.md` если изменились переменные
6. Обновить `dashboard-v2-usage.md` если изменились navigation/usage patterns
7. Запустить автоматизированные QA проверки
8. Сообщить о выполненных проверках, пропущенных проверках и статусе sync mirrors
