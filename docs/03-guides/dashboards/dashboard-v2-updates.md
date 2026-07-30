______________________________________________________________________

## UX report artifact requirement

Для любого PR с изменениями `grafana/dashboards/*.json` change notes MUST
содержать ссылку на UX artifact:
`docs/reports/dashboard-ux-checks/YYYY-MM-DD.md`.

Latest dashboard UX artifact for current shipped JSON changes:
`docs/reports/dashboard-ux-checks/2026-07-30.md`
(prior: `docs/reports/dashboard-ux-checks/2026-07-28-drmr.md`;
also: `docs/reports/dashboard-ux-checks/2026-07-28.md`; canonical baseline:
`docs/reports/dashboard-ux-checks/2026-05-19.md`)

## Selected-range description sync (2026-07-30)

- Control-plane panels backed by `$__range` now identify the selected range in
  their operator-facing descriptions.
- Global-scope and telemetry-absence caveats remain explicit.
- PromQL, layout, navigation, variables, and thresholds are unchanged.

## DRM residual migration (2026-07-28, epic #6844)

- Metrics Evidence replaces SCRAPING jargon on Runtime trust gate.
- DQ Now vs Range lanes no longer peer-compete on first path.
- Incident: Active Suspects by domain; Current Alerts + Alert State History (range).
- Run Explorer: pipeline-run-reports list + pipeline-run-report funnel/reasons/artifacts.
- Recording rules: retired `action_target=silver_reject_explorer` → `data_quality`.
- UX freshness gate: calendar today/yesterday (no frozen 2026-05-19 policy date).


Version: 1.0.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-19'

______________________________________________________________________

# Dashboard v2 Updates (Shipped Surface 2026-05-19)

> **Removed 2026-07-23:** Silver Reject Explorer dashboard, Loki/Tempo Explore adjuncts, Quarantine Explorer datasource (replaced by BioETL Ops HTTP on :8000).
> Use CLI ioetl quarantine inspect for record-level forensics. See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).



Источник истины: `grafana/dashboards/bioetl-*.json`

Этот changelog описывает **текущий shipped contract**, а не historical patch
notes. Если prose ниже расходится с JSON, править нужно prose, потому что JSON
остаётся SSOT.

## Dashboard System 2.0 (2026-07-28, epic #6800)

- Operator UX foundation: `operator-ux-v2.md`, `verdict-ontology.md`, `migration-map-v2.md`.
- First-screen evidence density on primary five boards; shared context shell retained.
- Adjunct workspaces: `bioetl-incident-v1`, `bioetl-run-explorer-v1` (portfolio = 7).
- Metrics Evidence remains the scrape/metrics-trust gate title (operator wording in description).
- First Action panels remain the primary CTA surface across boards.
- Provider causes use existing `bioetl_provider_current_cause` recording rules.

## Phase-2 residual (2026-07-28, epic #6828)

- SSOT: `dashboard-system-2.0-phase2-residual.md` (greenfield Unified Plan not executable).
- Visualization: color-background status tables; dual-row nav 0–4 / 5–6.
- Incident: domain-separated suspect tables (Runtime / Provider / DQ).
- Run Explorer: HTTP narrative + ≤4 next actions; nav owns board hops.
- Empty-state / CTA chrome standardized across boards.
- Usability re-measure: `reports/observability/usability-baseline.md` post-Phase-2 section.

## Проверенные дашборды

- `bioetl-overview-v2`
- `bioetl-control-plane-v1`
- `bioetl-dq-v2`
- `bioetl-provider-health-v2`
- `bioetl-runtime`
- `CLI quarantine inspect`
- `bioetl-workflow-overview`

## Current shipped baseline

- Все primary operator dashboards `0..5` используют `refresh: 60s` и
  `time.from=now-12h`.
- `CLI quarantine inspect` остаётся forensic exception с `refresh: 1m`
  и `time.from=now-24h`.
- Primary dashboards `0..5` используют shared context shell
  `$workflow`, `$pipeline`, `$run_type`, `$run_id`.
- `$workflow` теперь single-select with Include All на всех primary
  dashboards, включая `bioetl-workflow-overview`.
- `$pipeline` остаётся single-select; `bioetl-overview-v2` intentionally
  defaults to `All`, остальные pipeline-scoped dashboards fail-close к
  `unknown`.
- `$run_type` остаётся multi-select with Include All.
- `$run_id` остаётся HTTP-backed identity context через
  `/ops/control-plane/filter-options`; это не Prometheus label и не Silver
  forensic selector.
- `bioetl-workflow-overview` добавляет visible `$status`, `$step_status`,
  `$step_kind` и hidden handoff vars `$pipeline_context`, `$run_type_context`,
  `$provider_context`.
- `CLI quarantine inspect` остаётся единственным shipped dashboard с
  exact forensic narrowing selectors `$quarantine_run_id` и `$payload_hash`.

## Navigation contract now in force

- Каноническая top-level шина — text navigation panel `id=1000`.
- Dashboard-to-dashboard links используют `includeVars=false` и передают только
  allowlisted `var-*` target scope.
- Same-tab navigation остаётся обязательной для shipped dashboard handoff.
- Все восемь shipped navigation panels `id=1000` после bus `0..6` содержат
  global adjunct links `Silver Reject Explorer`, `Explore Logs`,
  `Explore Traces`.
- Текущий dashboard остаётся видимым как disabled theme-safe item; шина
  переносится на `1024px` и сохраняет контраст в dark/light themes.
- `Explore Traces` uses the explicit search-first Tempo route with the active
  dashboard range (`from=${__from}`, `to=${__to}`), `var-ds=tempo`,
  `var-groupBy=resource.service.name`, and stable low-cardinality TraceQL
  scope.

## First-screen / panel-title updates

- `bioetl-overview-v2` canonical CTA panel title = `First Action`
  (`id=215`).
- `bioetl-workflow-overview` removed the old `Workflow Scope` banner and now
  uses `First Action` (`id=9`) as the single justified first-screen
  dashboard-handoff CTA.
- Workflow selected-range evidence moved to `bioetl-runtime` workflow band:
  `Track Failed Workflow Runs`, `Track Failed Workflow Steps`. These panels
  use zero-valid fallback for empty selected ranges and render neutral evidence
  instead of colored verdicts when scrape/rule health is degraded.
- `bioetl-runtime` keeps `Metrics Evidence` as a first-screen datasource
  trust marker and now reserves readable dashboard width for that panel.
  `Status` / `Runtime Status` are trust-gated by this marker, and compact
  selected-range zero cards render as neutral evidence instead of green
  verdicts when scrape/rule health is degraded.
- `bioetl-control-plane-v1` keeps first-screen trust evidence dashboard-first:
  replay safety, checkpoint freshness, manifest/ledger integrity, telemetry
  missing, and `Review First Recovery Action` (next-step rail; id=906).

## Current key surfaces

- `bioetl-overview-v2`: `id=99`, `214`, `215`, `9300`, `9301`,
  `9002..9007`, `9013`, `9018..9021`
- `bioetl-control-plane-v1`: `id=891..894`, `906`, `907`, `908`, `130`,
  `9400..9407`
- `bioetl-runtime`: `id=9400..9403`, `9991`, `9100..9102`, `16`, `205`,
  `220`, `237`, `242`, `250..258`
- `bioetl-dq-v2`: `id=9400..9403`, `9100..9103`, `1`, `121`, `153..155`
- `bioetl-provider-health-v2`: `id=9400..9403`, `9002`, `9100..9103`,
  `1`, `2`, `7`, `31`, `32`, `102`, `104..114`
- `bioetl-workflow-overview`: `id=9400..9403`, `1..9`,
  collapsed `Step Diagnostics (collapsed)`
- `CLI quarantine inspect`: `id=1..10`

## 2026-05-19 remediation set

1. Formalized the `bioetl-control-plane-v1` navigation exception in active
   operator docs and removed the universal-doc claim that every `id=1000`
   must expose direct Explore adjunct links.
2. Synced selector docs to the shipped `$workflow` contract:
   single-select with Include All across primary dashboards.
3. Promoted workflow CTA naming from stale `Next Diagnostic Surface` mirrors to
   shipped `First Action`.
4. Updated panel-title/checklist/requirements/test-proposal mirrors to the
   current shipped workflow and overview titles.
5. Widened `bioetl-runtime` first-screen `Metrics Evidence` panel so the
   trust marker remains readable above fold.
6. Made Runtime status trust-gated by `Metrics Evidence` and neutralized
   compact selected-range zero cards so scrape/rule gaps visually outrank `0`
   evidence.
7. Converted `Workflow Run Outcomes / Range` from a colored bar gauge to a
   compact neutral `stat` for selected-range empty evidence.
8. Added fresh UX evidence and CI guards for active dashboard-doc drift.

## Validation pointers

- JSON SSOT: `grafana/dashboards/*.json`
- Navigation contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- Selector contract: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- Active operator docs:
  - `docs/03-guides/dashboards/README.md`
  - `docs/03-guides/dashboards/dashboard-v2-usage.md`
  - `docs/03-guides/dashboards/variable-reference.md`
  - `docs/05-operations/01-monitoring-guide.md`
  - `grafana/README.md`
