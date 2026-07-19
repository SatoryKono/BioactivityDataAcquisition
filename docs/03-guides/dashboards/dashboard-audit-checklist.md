# Dashboard Audit Checklist

**Version**: 1.2.0
**Status**: active
**Date**: 2026-07-13
**Source of truth**: `grafana/dashboards/*.json`, `docs/03-guides/dashboards/contracts/*.yaml`

## Usage

Use this checklist to verify that a dashboard complies with BioETL requirements. Each section corresponds to a requirement category from the design system.

Run automated checks first:
```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
uv run python -m scripts.engineering.qa report-dashboard-query-duplicates
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
```

---

## 1. One Big Question and First-Screen Preamble

### 1.1 Dashboard Question (MUST)
- [ ] Dashboard answers exactly one `ONE BIG QUESTION`
- [ ] Secondary questions stay in supporting panels, collapsed-by-default below-fold rows, tabs, or drilldowns
- [ ] Primary KPI/verdict is visible on the first screen without scroll

### 1.2 Scope / Provenance Block (MUST for operator dashboards)
- [ ] First screen shows current scope in dashboard-family terms (`pipeline`, `run_type`, `provider`, `workflow`, etc.)
- [ ] First screen or adjacent context row shows provenance:
  - [ ] sources / systems / tables / endpoints / metric families
  - [ ] update cadence / schedule
  - [ ] transformation or runtime version (`git_commit`, artifact or equivalent)
  - [ ] last successful run / last refresh in UTC
  - [ ] owner / contact

### 1.3 Availability / Risk Block (MUST)
- [ ] SLA or expected freshness window is stated
- [ ] Known limitations / source lag / partial-scope caveats are stated
- [ ] Sensitivity / access classification is stated or explicitly delegated to the monitoring guide/runbook

### 1.4 First Action (MUST)
- [ ] First screen contains a concise `What to do next` / `First action`
- [ ] `CRIT` and `WARN` paths are distinguishable

---

## 2. Navigation and Top-Level Structure

### 2.1 Navigation Bus (MUST)
- [ ] Dashboard has navigation panel with `id=1000`
- [ ] Navigation panel includes full bus: `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO`
- [ ] Current dashboard is rendered as a disabled theme-safe item
- [ ] Machine-readable `panel.links` omit self-links (no duplicate navigation)
- [ ] All navigation links open in same tab (`targetBlank: false`)
- [ ] Bus remains readable in dark/light themes, has visible focus/hover states, and wraps without clipping at `1024px`

### 2.2 Global Adjunct Links (MUST)
- [ ] After bus `0..6`, includes `Silver Reject Explorer`
- [ ] Includes `Explore Logs` with safe baseline `{job="bioetl"}`
- [ ] Includes `Explore Traces` (adjunct, traced-run-only)
- [ ] Explore Traces tooltip mentions traced-run-only requirement

### 2.3 Link Semantics (MUST)
- [ ] No duplicate dashboard-to-dashboard links to same target
- [ ] No legacy link titles: `Back to Overview`, `5. Control Plane`, `Explore Logs (Loki, tracing profile)`, `Next Recommended Drilldown`
- [ ] All links use canonical titles from `navigation-contract.md`

### 2.4 Variable Handoff in Links (MUST)
- [ ] All links have `includeVars: false`
- [ ] Target-scoped variables passed explicitly in URL (`var-*`)
- [ ] Forensic IDs (`quarantine_run_id`, `payload_hash`) NOT passed to non-target dashboards
- [ ] Cross-scope links have tooltip with `Scope reset: ...` suffix
- [ ] Same-scope links have tooltip: `Preserves selected scope and time range.`

### 2.5 Required Top-Level Links by UID (MUST)
Check against `contracts/navigation-links.yaml` → `required_top_level_links_by_uid`:
- [ ] `bioetl-overview-v2`: 0. Control Plane, 2. Runtime, 3. Provider Health, 4. Data Quality, 5. Workflow, 6. Alerts & SLO, Explore Logs, Explore Traces, Silver Reject Explorer
- [ ] `bioetl-runtime`: 0. Control Plane, 1. Overview, 3. Provider Health, 4. Data Quality, 5. Workflow, 6. Alerts & SLO, Explore Logs, Explore Traces, Silver Reject Explorer
- [ ] `bioetl-control-plane-v1`: 1. Overview, 2. Runtime, 3. Provider Health, 4. Data Quality, 5. Workflow, 6. Alerts & SLO, Silver Reject Explorer, Explore Logs, Explore Traces
- [ ] `bioetl-provider-health-v2`: 0. Control Plane, 1. Overview, 2. Runtime, 4. Data Quality, 5. Workflow, 6. Alerts & SLO, Explore Logs, Explore Traces, Silver Reject Explorer
- [ ] `bioetl-dq-v2`: 0. Control Plane, 1. Overview, 2. Runtime, 3. Provider Health, 5. Workflow, 6. Alerts & SLO, Silver Reject Explorer, Explore Logs, Explore Traces
- [ ] `bioetl-silver-reject-explorer`: 0. Control Plane, 1. Overview, 2. Runtime, 3. Provider Health, 4. Data Quality, 5. Workflow, 6. Alerts & SLO, Explore Logs, Explore Traces
- [ ] `bioetl-workflow-overview`: 0. Control Plane, 1. Overview, 2. Runtime, 3. Provider Health, 4. Data Quality, 6. Alerts & SLO, Explore Logs, Explore Traces, Silver Reject Explorer
- [ ] `bioetl-alerts-slo`: 0. Control Plane, 1. Overview, 2. Runtime, 3. Provider Health, 4. Data Quality, 5. Workflow, Silver Reject Explorer, Explore Logs, Explore Traces

---

## 3. Variables and Selectors

### 3.1 Variable Descriptions (MUST)
- [ ] Every variable in `templating.list` has non-empty `description`

### 3.2 Selector Contract Compliance (MUST)
Check against `contracts/selector-contracts.yaml` → `shipped_selector_registry`:

**Pipeline summary dashboards** (`bioetl-control-plane-v1`, `bioetl-overview-v2`, `bioetl-runtime`, `bioetl-dq-v2`):
- [ ] Visible selectors: `pipeline`, `run_type` (plus optional `stage` for runtime/dq)
- [ ] No forensic identifiers (`quarantine_run_id`, `payload_hash`)
- [ ] No exact run selection without run catalog

**Provider-first** (`bioetl-provider-health-v2`):
- [ ] Visible selector: `provider`
- [ ] Hidden context selector: `pipeline_context`
- [ ] Hidden detail selector: `adapter`

**Workflow evidence** (`bioetl-workflow-overview`):
- [ ] Visible selectors: `workflow`, `status`, `step_status`, `step_kind`
- [ ] Hidden context selectors: `pipeline_context`, `run_type_context`, `provider_context`
- [ ] No visible `pipeline` / `run_type` selectors

**Forensic explorer** (`bioetl-silver-reject-explorer`):
- [ ] Visible selectors: `pipeline`, `run_type`, `reason_code`, `field`, `quarantine_run_id`, `payload_hash`
- [ ] Forensic selectors do NOT leak into Prometheus dashboards

### 3.3 Variable Defaults and Selection Modes (MUST)
- [ ] `$pipeline`: single-select, default `All` only on `bioetl-overview-v2`, otherwise `unknown`
- [ ] `$run_type`: multi-select with Include All, default `All`/`$__all` (NOT `unknown`)
- [ ] `$provider`: single-select, default `unknown` (provider-health only)
- [ ] `$stage`: multi-select with Include All (runtime/dq only)
- [ ] Forensic variables (`quarantine_run_id`, `payload_hash`): local to explorer, NOT in cross-dashboard links

### 3.4 Hidden Context Variables (MUST)
- [ ] Hidden vars justified by return-path or detail-only scope
- [ ] Hidden vars do NOT automatically become visible selectors
- [ ] No blanket `includeVars=true` semantics for cross-dashboard navigation

### 3.5 Variable Dependency Chains (MUST)
- [ ] `bioetl-runtime`: `$run_type` depends on `$pipeline`, `$stage` depends on runtime-selected scope
- [ ] `bioetl-dq-v2`: `$run_type` depends on `$pipeline`, `$stage` depends on `$pipeline` and `$run_type`
- [ ] `bioetl-provider-health-v2`: `$pipeline_context` preserved from source, `$adapter` optional
- [ ] `bioetl-silver-reject-explorer`: `$pipeline` required before Quarantine Explorer reads
- [ ] `bioetl-workflow-overview`: workflow variables local, hidden context preserves single-pipeline handoff

---

## 4. Design System and Visualization

### 4.1 Status Semantics (MUST)
**L0 operator dashboards** (`0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`):
- [ ] `0` maps to `OK` (green)
- [ ] `1` maps to `WARN` (orange)
- [ ] `>=2` maps to `CRIT` (red)
- [ ] `null` maps to `UNKNOWN` (gray)
- [ ] Trusted Control/Runtime headline cards override the generic mapping with `3 → INCOMPLETE` (gray) when required evidence is missing or stale
- [ ] Query-backed surfaces distinguish terminal `VALID EMPTY`, `TELEMETRY ABSENT`, `N/A`, and explicit `ERROR` from transient `LOADING`; blank accepted renders are forbidden

**Diagnostic dashboards only**:
- [ ] If using alias terms (`DEGRADED`, `BROKEN`, `HEALTHY`), description includes alias mapping

### 4.2 Threshold Configuration (MUST)
For all status panels (`stat`/`gauge`):
- [ ] `fieldConfig.defaults.color.mode = thresholds`
- [ ] `fieldConfig.defaults.thresholds.mode = absolute`
- [ ] Threshold steps: `green` (null), `orange` (1), `red` (2)
- [ ] For designated first-screen current-status stat panels:
  - [ ] `options.colorMode = background`
  - [ ] Explicit value mapping exists: `0 -> OK`, `1 -> WARN`, `2 -> CRIT`, `null -> UNKNOWN`

### 4.3 Panel-Type Visualization Standards (MUST)
- [ ] **Current-status stat**: `colorMode=thresholds`, `background` for designated severity cards, `null -> UNKNOWN` mapping where fail-closed
- [ ] **Selected-range trend stat**: `colorMode=value`, `graphMode=area`
- [ ] **Selected-range count stat**: `colorMode=value`, `graphMode=none`, `or vector(0)` only if missing series = zero events
- [ ] **Percentage/score/latency gauge**: `showThresholdMarkers=true`, `showThresholdLabels=false` (unless documented exception)
- [ ] **Status table column**: `custom.cellOptions.type=color-background`
- [ ] **Data table**: `custom.cellOptions.type=auto` when default configured
- [ ] **Comparative timeseries**: `tooltip.mode=multi`, `tooltip.sort=desc`
- [ ] **Scalar trend timeseries**: `tooltip.mode=single`, `tooltip.sort=none` or omitted

### 4.4 Panel Titles (MUST)
- [ ] All new panels use action-first titles with verb at start
- [ ] Template: `<Action Verb>: <Object/Signal> [<Window>]`
- [ ] Verbs: `Monitor`, `Inspect`, `Track`, `Compare`, `Review`
- [ ] Examples: `Monitor: Runtime Failure Rate [24h]`, `Inspect: Provider Retry Saturation [1h]`

### 4.5 Panel Descriptions (MUST)
For each panel:
- [ ] Description includes what is measured (1 sentence)
- [ ] Description includes how to interpret `OK/WARN/CRIT/UNKNOWN`
- [ ] Description includes link to runbook/drilldown if applicable

---

## 5. Layout and Structure

### 5.1 First-Screen Responsibility (MUST)
- [ ] Dashboard answers its primary operator question on first screen (no scroll)
- [ ] Current-status/verdict panels do NOT use `$__range`
- [ ] Range panels include selected-range wording in title or description
- [ ] Deep details (`run_id`, `payload_hash`, record-level tables) NOT on first-screen status rows

**Dashboard-specific first-screen questions**:
- [ ] `bioetl-overview-v2`: What is currently broken/degraded and where to drill down first?
- [ ] `bioetl-runtime`: What is blocking runtime execution right now?
- [ ] `bioetl-provider-health-v2`: Which provider is degraded/failing and why?
- [ ] `bioetl-dq-v2`: What is current DQ state and first action?
- [ ] `bioetl-control-plane-v1`: Can we trust control plane and safely replay/resume?

### 5.2 Panel Decision Matrix (MUST)
- [ ] Current status / current reason panels: on first screen, fixed current windows, NOT `$__range`
- [ ] Next action / route panels: on first screen, low-cardinality route/action rules
- [ ] Selected-range count/rate/trend panels: below first screen (except compact L0 context), MUST use `$__range`
- [ ] Raw counter / histogram / latency evidence panels: below first screen
- [ ] Forensic row/table/details panels: below first screen or in dedicated explorer

### 5.3 Layout Grammar by Dashboard Role (MUST)
- [ ] Every shipped dashboard answers primary operator question before first evidence-heavy row
- [ ] Historical or selected-range evidence does NOT visually precede current-state answer on L0/L1/L2 dashboards
- [ ] Forensic explorer surfaces keep scope semantics and first action above row-level detail

### 5.4 Visibility Tiers (MUST)
- [ ] **Tier 1** (always-visible answer surface): current status, verdict, first action, current causes
- [ ] **Tier 2** (always-visible supporting context): KPI context, trust markers, bounded mirrors
- [ ] **Tier 3** (below-fold evidence): selected-range evidence
- [ ] **Tier 4** (collapsed-by-default diagnostics): tracing-only, raw, verbose, rare forensic breakdowns; full audits expand these rows explicitly
- [ ] Critical signal does NOT live exclusively inside a diagnostic row

### 5.5 GridPos Layout (MUST)
- [ ] Top-level `gridPos` rectangles do NOT overlap
- [ ] Navigation, scope, first-action, current-status, range evidence, and collapsible rows occupy explicit non-overlapping bands
- [ ] No unexplained empty row gaps between adjacent bands (unless justified in audit/docs)

### 5.6 Collapsed Row Policy (MUST)
- [ ] Tracing-only, raw, verbose, or not-required-for-first-pass-triage panels are grouped in rows collapsed by default
- [ ] Collapsed rows have descriptive titles by incident scenario (e.g., `Incident Drilldown: ...`)

---

## 6. Data and Metrics

### 6.1 No-Data/Unknown Policy (MUST)
- [ ] No silent treatment of no-data as OK for status panels
- [ ] If no-data truly equals zero events, query uses explicit `... or vector(0)` and description confirms this
- [ ] In all other cases, no-data remains `UNKNOWN`
- [ ] `null` renders as `UNKNOWN` with gray color
- [ ] `or vector(0)` used only for true zero-event counters where missing series semantically means zero events

### 6.2 Missing-Data Semantics by Panel Class (MUST)
- [ ] **Current-status / current-cause panels**: `null` → `UNKNOWN`, `or vector(0)` forbidden
- [ ] **Zero-valid event counters**: `or vector(0)` allowed only if missing series = zero events, visible in query or description
- [ ] **Timeseries / latency / histogram evidence**: `No data` remains diagnostic signal, NOT synthetic healthy value
- [ ] **Forensic tables / HTTP-backed explorer**: distinguish valid empty result vs unsupported filter chain vs backend failure
- [ ] **Trust-marker panels**: present only where operator cannot safely interpret first-screen verdict without them

### 6.3 Datasource Trust Semantics (MUST)
- [ ] Prometheus current-status and current-cause panels remain fail-closed (preserve `UNKNOWN`, no `or vector(0)`)
- [ ] `or vector(0)` valid only for true zero-event counters
- [ ] Explicit trust marker added only when operator could otherwise confuse empty scope, telemetry gap, or backend failure
- [ ] HTTP-backed forensic surfaces distinguish: valid scope with zero rows vs invalid filter chain vs backend failure

---

## 7. Units and Decimals (MUST)
- [ ] Event counters (`... Missing`, `... Incompatibilities`, `... Failures`): `unit=short`, `decimals=0`
- [ ] Timestamp KPI (`Latest Successful Data Timestamp`): `unit=dateTimeAsIso`, `decimals=0`
- [ ] Fractions/percentages (`... Rate`, `... Ratio`): consistent unit within dashboard family (`percentunit` or `percent`), consistent `decimals` (usually `0` or `2`)
- [ ] Similar KPI across different dashboards has identical `unit/decimals` pair

---

## 8. JSON Invariants

### 8.1 Root Fields (MUST)
- [ ] `timezone`: `"browser"`
- [ ] `style`: `"dark"`
- [ ] `editable`: `true`
- [ ] `graphTooltip`: `1`
- [ ] `hideControls`: if present, MUST be `false`

### 8.2 Metadata Policy (MUST)
- [ ] `refresh` and default `time.from` follow `contracts/navigation-links.yaml`:
  - [ ] L0/L1 dashboards: `time.from=now-12h`, `refresh=30s`
  - [ ] L2 forensic (`silver-reject-explorer`): `time.from=now-24h`, `refresh=1m`
- [ ] `schemaVersion` MAY remain `30` or `39` until explicit Grafana migration decision
- [ ] `iteration`: if present, MUST be positive integer
- [ ] `tags`: MUST include `bioetl`, MAY include role/domain tags

### 8.3 Export Noise (NOT correctness failure)
- [ ] Mixed panel-level `pluginVersion` values NOT treated as standalone correctness failure
- [ ] No bulk-rewrite of shipped dashboard JSON just to force one `pluginVersion` across suite without proven regression

---

## 9. Navigation Link Details

### 9.1 Link Title Style (MUST)
- [ ] Top-level links use canonical names from navigation contract
- [ ] Action-link vocabulary: `Back to <Dashboard>`, `Open <Target>`, `Investigate <Target>`
- [ ] `Back to <Dashboard>` only for return to previous L0 level
- [ ] `Open <Target>` for transition to neighboring dashboard or external runbook
- [ ] `Investigate <Target>` for transition to forensic/deep-dive surface

### 8.2 Scope Reset Tooltip (MUST)
- [ ] If link changes scope (e.g., forces `var-pipeline=unknown`, resets provider/adapter), tooltip contains explicit suffix: `Scope reset: ...`
- [ ] Recommended template: `Cross-scope handoff ... Scope reset: pipeline=unknown, run_type=All; provider/adapter not transferred.`
- [ ] If scope does not change, tooltip: `Preserves selected scope and time range.`

### 8.3 Role-Based Runbook CTA Policy (MUST)
- [ ] Operator/forensic surfaces (`runtime`, `control-plane`, `provider-health`, `dq`, `silver-reject-explorer`): critical panels SHOULD have actionable CTA
- [ ] Dashboard-routing-first surface (`overview`): panel-level CTA MAY remain dashboard-only
- [ ] Selected-range evidence surface (`workflow-overview`): selected-range evidence counters do NOT require panel-level runbook links
- [ ] If runbook link used, URL follows canonical GitHub blob pattern: `https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/<name>.md`
- [ ] Runbook link titles remain domain-specific (`Open Runtime Troubleshooting Runbook`, `Open Provider Incident Runbook`), NOT generic `Open Runbook`

---

## 9. Actionable Links for Critical Panels (MUST)
For P1/P2 operator panels (`stat`/`gauge`/`table`):
- [ ] `options.dataLinks` contains at least one object
- [ ] `title` starts with `Open <target>` pattern
- [ ] `url` leads to target dashboard/runbook for drilldown

---

## 10. PromQL Duplication Policy (MUST)

### 10.1 Audit Surface
Run: `uv run python -m scripts.engineering.qa report-dashboard-query-duplicates`

### 10.2 Normative Rules
- [ ] Exact duplicate PromQL across more than one panel is either:
  - [ ] Intentionally reused with role-specific justification, OR
  - [ ] Consolidated into recording rule or single canonical panel surface
- [ ] Near-duplicate query families remain panel-local only when expressing same metric family as sibling breakdown (percentile triplets, stage-specific variants)
- [ ] If same query family repeats across multiple panels/dashboards, priority is:
  1. [ ] Recording rule / shared canonical metric
  2. [ ] Explicit justification in dashboard audit/tests
  3. [ ] Raw duplication only as temporary exception

### 10.3 Audited Exact-Duplicate Reuse
- [ ] `bioetl_dq_current_status` intentionally serves the compact `Status` and expanded `Monitor DQ Current Status` panels
- [ ] `bioetl_runtime_current_status_trusted` intentionally serves the compact `Status` and expanded `Runtime Status` panels
- [ ] DQ weighted stat and trend have distinct time semantics: fixed seven-day (`[7d]`) retained snapshot versus raw selected-range samples; absence remains `UNKNOWN`
- [ ] `Monitor: Lineage Refs Missing` remains canonical in `bioetl-control-plane-v1`
- [ ] `bioetl-dq-v2` uses a handoff note/link instead of duplicating the metric
- [ ] Justified exact duplicates are present in the query-duplicate allowlist and query-governance integration tests

---

## 11. KPI Ownership (MUST)

### 11.1 Canonical Dashboard Mapping
- [ ] System Status → canonical: `1. Overview`; trusted derivatives: `2. Runtime`, `0. Control Plane`
- [ ] First Action → canonical: `1. Overview`, mirrors: `2. Runtime`, `3. Provider Health`
- [ ] L0 Inputs → canonical: `1. Overview`, mirrors: `2. Runtime`, `4. Data Quality`, `0. Control Plane`
- [ ] Gold Lifecycle → canonical: `1. Overview`, mirrors: `2. Runtime`, `0. Control Plane`
- [ ] Provider Global → canonical: `1. Overview`, mirrors: `3. Provider Health`
- [ ] Workflow Selected → canonical: `1. Overview`, mirrors: `5. Workflow`
- [ ] Workflow Global → canonical: `1. Overview`, mirrors: `5. Workflow`
- [ ] Replay Safety State → canonical: `0. Control Plane`, mirrors: `1. Overview`, `2. Runtime`
- [ ] Checkpoint Freshness Proxy → canonical: `0. Control Plane`, mirrors: `2. Runtime`
- [ ] Ledger/Manifest Consistency → canonical: `0. Control Plane`, mirrors: `2. Runtime`
- [ ] Provider Health (aggregated) → canonical: `3. Provider Health`, mirrors: `1. Overview`, `2. Runtime`
- [ ] DQ Status → canonical: `4. Data Quality`, mirrors: `1. Overview`, `2. Runtime`

### 11.2 Mirror Policy
- [ ] Secondary dashboard cards duplicating canonical KPI without new measurement are removed or renamed as navigational shortcut
- [ ] Preserved mirror cards have title/description explicitly indicating mirror, not primary source of truth
- [ ] Secondary mirror cards do NOT add dashboard-to-dashboard links if target already in top-level bus
- [ ] If mirror adds value (e.g., provider-scoped breakdown), indicated in description without duplicating navigation link

---

## 12. Time Handoff (MUST)
- [ ] Dashboard links include required token: `${__url_time_range}`
- [ ] Explore links include required tokens: `from=${__from}`, `to=${__to}`

---

## 13. Required Panel Links by UID (MUST)
Check against `contracts/navigation-links.yaml` → `required_panel_links_by_uid`:

**bioetl-overview-v2**:
- [ ] Panel `214` (System Status) → dataLinks to: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `215` (First Action) → dataLinks to: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `9002` (L0 Inputs) → dataLinks to: Open Runtime, Open Control Plane, Open Data Quality, Open Provider Health, Open Workflow
- [ ] Panel `9003` (Runtime Blockers) → dataLink to: Open Runtime
- [ ] Panel `9004` (DQ Status) → dataLink to: Open Data Quality
- [ ] Panel `9005` (Gold Lifecycle) → dataLink to: Open Runtime
- [ ] Panel `9006` (Control Plane) → dataLink to: Open Control Plane
- [ ] Panel `9007` (Provider Global) → dataLink to: Open Provider Health
- [ ] Panel `9008` (Workflow Selected) → dataLink to: Open Workflow
- [ ] Panel `9013` (Workflow Global) → dataLink to: Open Workflow

**bioetl-dq-v2**:
- [ ] Panel `9102` (Inspect DQ Current Reasons) → dataLink to: Open Silver Reject Explorer

**bioetl-workflow-overview**:
- [ ] Panel `9` (First Action) → dataLinks to: Open 2. Runtime, Open 4. Data Quality, Open 3. Provider Health, Open 0. Control Plane, Open 1. Overview

---

## 14. First Action Contract (MUST)
Check against `contracts/navigation-links.yaml` → `first_action_contract`:

**bioetl-runtime** (panel `9991`):
- [ ] Min CTA: 4, Max CTA: 4
- [ ] CTAs: Review current status, Review range evidence, Inspect top blockers, Inspect active blocker

**bioetl-provider-health-v2** (panel `9002`):
- [ ] Min CTA: 3, Max CTA: 3
- [ ] CTAs: Review severity matrix, Inspect critical providers, Inspect provider top causes

**bioetl-dq-v2** (panel `9103`):
- [ ] Min CTA: 3, Max CTA: 3
- [ ] CTAs: Review current status, Inspect current reasons, Open Silver Reject Explorer

**bioetl-silver-reject-explorer** (panel `10`):
- [ ] Min CTA: 2, Max CTA: 2
- [ ] CTAs: Review total rejects, Review scoped summary

---

## 15. Test Coverage (MUST)

### 15.1 Automated Test Checks
Run:
```bash
pytest tests/integration/test_grafana_dashboard_links.py
pytest tests/integration/test_grafana_config.py
pytest tests/integration/test_grafana_selector_contract.py
pytest tests/integration/test_grafana_variable_reference.py
```

- [ ] Links contract test passes
- [ ] Variable contract test passes
- [ ] Selector taxonomy test passes
- [ ] Variable reference mirror test passes
- [ ] Exact-id isolation test passes (`run_id` forbidden in Prometheus labels,
  preserved only across primary dashboard links; `quarantine_run_id`/`payload_hash`
  remain forbidden in generic cross-dashboard links)

### 15.2 First-Screen Contract Test
- [ ] `tests/integration/test_grafana_dashboard_first_screen_contract.py` validates no top-level `gridPos` overlaps

### 15.3 Visual Semantics Test
- [ ] `scripts.engineering.qa check-dashboard-visual-semantics` validates:
  - [ ] color mode = `thresholds`
  - [ ] standardized threshold steps
  - [ ] mandatory `UNKNOWN` mapping for `null`
  - [ ] `background` colorMode + explicit `OK/WARN/CRIT` value mappings for designated current-status severity stat panels

---

## 16. Sources of Truth (MUST)

### 16.1 Machine-Readable Contracts
- [ ] Dashboard JSON: `grafana/dashboards/*.json`
- [ ] Navigation contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- [ ] Selector contract: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`

### 16.2 Human-Readable Mirrors
- [ ] Variable reference: `docs/03-guides/dashboards/variable-reference.md`
- [ ] Selector architecture: `docs/03-guides/dashboards/selector-architecture.md`
- [ ] Design system: `docs/03-guides/dashboards/design-system.md`
- [ ] Dashboard usage: `docs/03-guides/dashboards/dashboard-v2-usage.md`
- [ ] Navigation contract: `docs/03-guides/dashboards/navigation-contract.md`
- [ ] Monitoring index: `docs/03-guides/dashboards/monitoring-index.md`

### 16.3 Mirror Sync Policy
- [ ] Markdown guides reference YAML contracts instead of redefining normative rules
- [ ] Changes to JSON/dashboard behavior update runtime source first, then sync docs mirrors
- [ ] No conflicting definitions between YAML contracts and Markdown mirrors

---

## 17. Cross-Scope Marker Contract (MUST)
Check against `contracts/navigation-links.yaml` → `cross_scope_marker_contract`:

### 17.1 Required Markers
- [ ] Reset scope marker: `Reset scope`
- [ ] Context mapping marker: `Context mapping`

### 17.2 Required Titles by Transition
- [ ] `bioetl-control-plane-v1 -> bioetl-provider-health-v2`: context mapping
- [ ] `bioetl-control-plane-v1 -> bioetl-workflow-overview`: reset scope
- [ ] `bioetl-provider-health-v2 -> bioetl-overview-v2`: context mapping
- [ ] `bioetl-provider-health-v2 -> bioetl-runtime`: context mapping
- [ ] `bioetl-provider-health-v2 -> bioetl-control-plane-v1`: context mapping
- [ ] `bioetl-provider-health-v2 -> bioetl-dq-v2`: context mapping
- [ ] `bioetl-provider-health-v2 -> bioetl-workflow-overview`: reset scope
- [ ] `bioetl-overview-v2 -> bioetl-provider-health-v2`: context mapping
- [ ] `bioetl-overview-v2 -> bioetl-workflow-overview`: reset scope
- [ ] `bioetl-runtime -> bioetl-provider-health-v2`: context mapping
- [ ] `bioetl-runtime -> bioetl-workflow-overview`: reset scope
- [ ] `bioetl-dq-v2 -> bioetl-provider-health-v2`: context mapping
- [ ] `bioetl-dq-v2 -> bioetl-workflow-overview`: reset scope
- [ ] `bioetl-provider-health-v2 -> bioetl-silver-reject-explorer`: context mapping
- [ ] `bioetl-silver-reject-explorer -> bioetl-provider-health-v2`: context mapping
- [ ] `bioetl-workflow-overview -> bioetl-provider-health-v2`: context mapping

### 17.3 Required Tooltip Tokens
- [ ] Reset scope tooltips contain: `Reset scope`
- [ ] Context mapping tooltips contain: `Context mapping`

---

## 18. Provider Context Mapping Contract (MUST)
Check against `contracts/navigation-links.yaml` → `provider_context_mapping_contract`:

### 18.1 Source Dashboard Values
- [ ] `bioetl-control-plane-v1`: provider_value=unknown, adapter_value=null
- [ ] `bioetl-overview-v2`: provider_value=unknown, adapter_value=unknown
- [ ] `bioetl-runtime`: provider_value=unknown, adapter_value=unknown
- [ ] `bioetl-dq-v2`: provider_value=unknown, adapter_value=unknown
- [ ] `bioetl-silver-reject-explorer`: provider_value=unknown, adapter_value=unknown

---

## 19. Documentation Updates (MUST for Changes)

### 19.1 When Modifying Dashboard Behavior
- [ ] Update runtime source first (`grafana/dashboards/*.json`)
- [ ] Update YAML contracts if behavior changes (`navigation-links.yaml`, `selector-contracts.yaml`)
- [ ] Sync docs mirrors if behavior or contributor guidance changed
- [ ] Update `panel-title-inventory.md` if panel titles changed
- [ ] Update `variable-reference.md` if variables changed
- [ ] Update `dashboard-v2-usage.md` if navigation/usage patterns changed

### 19.2 Post-Change Validation
- [ ] Re-scan impacted code/config/doc/runtime surfaces before finalizing
- [ ] Use repo search plus memory/evidence anchors to find related tests, docs, contracts, configs, workflows
- [ ] Run automated QA checks
- [ ] Report checks run, skipped checks, and mirror-sync status explicitly

---

## 20. Exception Documentation (MUST for Deviations)

### 20.1 When Deviating from Requirements
- [ ] Exception explicitly documented in dashboard audit or docs
- [ ] Justification includes operator rationale
- [ ] Exception reviewed and approved
- [ ] Exception tracked in project debt/exception register if recurring

### 20.2 Temporary Exceptions
- [ ] Temporary exception has explicit remediation plan
- [ ] Temporary exception has target date for resolution
- [ ] Temporary exception referenced in relevant tests/docs

---

## Audit Summary

**Dashboard UID**: _______________
**Dashboard Title**: _______________
**Auditor**: _______________
**Date**: _______________

### Overall Status
- [ ] PASS - All MUST requirements satisfied
- [ ] PASS with documented exceptions - All MUST requirements satisfied with documented justifications
- [ ] FAIL - One or more MUST requirements not satisfied

### Critical Failures (MUST)
List any unchecked MUST items:

### Warnings (SHOULD)
List any SHOULD items not satisfied:

### Exceptions Documented
List any documented exceptions with justifications:

### Automated Test Results
- [ ] `check-dashboard-visual-semantics`: PASS/FAIL
- [ ] `report-dashboard-query-duplicates`: PASS/FAIL (review output)
- [ ] `report-dashboard-inventory --check`: PASS/FAIL
- [ ] `test_grafana_dashboard_links.py`: PASS/FAIL
- [ ] `test_grafana_selector_contract.py`: PASS/FAIL
- [ ] `test_grafana_variable_reference.py`: PASS/FAIL

### Recommendations
Optional improvements or observations:

---

## References

- Design System: `docs/03-guides/dashboards/design-system.md`
- Navigation Contract: `docs/03-guides/dashboards/navigation-contract.md`
- Selector Architecture: `docs/03-guides/dashboards/selector-architecture.md`
- Variable Reference: `docs/03-guides/dashboards/variable-reference.md`
- Dashboard Usage: `docs/03-guides/dashboards/dashboard-v2-usage.md`
- Monitoring Index: `docs/03-guides/dashboards/monitoring-index.md`
- Navigation Links YAML: `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- Selector Contracts YAML: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- Panel Title Inventory: `docs/03-guides/dashboards/panel-title-inventory.md`
