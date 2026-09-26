______________________________________________________________________

## UX report artifact requirement

The GR-DB-CORR acceptance report `docs/reports/dashboard-ux-checks/2026-09-21.md`
records observed improvements and remaining verification gaps.

## State and navigation follow-up — 2026-09-14

All seven dashboards now distinguish missing evidence from measured empty
results. The change corrects selected verdicts, Provider handoffs, Trust reason
wrapping, full evidence tables, stage coverage, terminal event age and DQ history.
See `docs/reports/dashboard-ux-checks/2026-09-14.md`
for the browser observations and the limits of this validation pass.

## Run Explorer simplification — 2026-09-13

Run Explorer now contains navigation, a scope banner and the last ten launches
in one table without pagination. Selected Run Details and Browse Workflow Runs
were removed with their nested panels. The banner starts Pipeline on a new line;
incoming run links select a row without targeting a removed panel. Report links
continue to open the exact row's report.

Current UX artifact: `docs/reports/dashboard-ux-checks/2026-09-13.md`.

## Earlier changes

Tables and accounting presentation (#10178, #10179, #10180, #10192, #10183):
selected-run summaries put status, coverage and local timestamps before the
UUID. Recent-run timestamps use reserved widths; workflow runs have direct
report links and a compact selection marker. Provider severity codes use the
same named states in summary and fleet detail. Optional latency uses a stat.
DQ range cards share a two-column grid, height and value font size. Current DQ
reasons distinguish explicit OK from unavailable evidence. Processed-record
counts and percentages are neutral quantities; layer label colors identify
Bronze/Silver/Gold, not quality. Percentages use one to three decimal places
consistently, preserving small exclusions and UNKNOWN denominators.

Для любого PR с изменениями `grafana/dashboards/*.json` change notes MUST
содержать ссылку на UX artifact:
`docs/reports/dashboard-ux-checks/YYYY-MM-DD.md`.

Previous dashboard UX artifact:
`docs/reports/dashboard-ux-checks/2026-09-07.md`. The Overview, Runtime and
Incident follow-up (#10176, #10177, #10181, #10193, #10194) adds readable
routing priorities, a first-screen blocker action, explicit global incident
scope and unverified confidence, complete alert names and neutral telemetry
evidence. Common navigation uses three grid rows on all seven dashboards;
the existing text sizes and query budgets remain unchanged.

Panel 205 now evaluates the
selected window once and preserves absent counters. Incident 2010 combines the
three recorded ranking metrics in one short union so Priority has one numeric
field before sorting. The earlier long raw-query union limitation no longer
applies to these recorded metrics.
(prior: `docs/reports/dashboard-ux-checks/2026-08-17.md`)
(prior: `docs/reports/dashboard-ux-checks/2026-08-11.md`;
visual-audit closeout: sequential expanded-row bands and a compact Incident
alert-state history layout, without query or verdict changes)
(prior: `docs/reports/dashboard-ux-checks/2026-08-05.md`)
(prior: `docs/reports/dashboard-ux-checks/2026-07-30.md`;
threshold-only repair: shipped dashboards now use the canonical gray base
threshold color without changing queries or operator workflows)
(prior: `docs/reports/dashboard-ux-checks/2026-07-28-drmr.md`;
also: `docs/reports/dashboard-ux-checks/2026-07-28.md`; canonical baseline:
`docs/reports/dashboard-ux-checks/2026-05-19.md`)

## First-window containment gate and dense P1 tables (2026-08-17)

- Render evidence now records per-panel first-window containment
  (`clientHeight`/`scrollHeight`/`clientWidth`/`scrollWidth`) and fails closed
  on internal overflow for text, stat, and summary-table panels (`#8896`).
- Provider Health first-screen tables are capped at four worst/deviating rows;
  `9104` ends at row 18 and the fold-straddle allowlist is retired (`#8900`).
- Incident `Inspect Ranked Suspects` keeps domain/signal provenance and an
  outer five-row cap (`#8902`). A single union query exceeds the first-screen
  PromQL length budget, so the bound is `topk(5)` per domain plus a Grafana
  `limit=5`.
- Run Explorer first screen shows the latest four runs and 4-row
  identity/accounting summaries; the last-20 browser and full tables stay in
  Selected Run Details (`#8903`).

## P2 first-window copy compaction (2026-08-17)

- Overview, Trust, Pipeline Diagnostics, and Data Quality first-window text
  panels keep the operator question or primary action and move selection
  procedures, pipeline examples, and coverage caveats into descriptions.
- Overview `Review Domain Status` (`9002`) is now a `topk(4)` deviation-first
  summary; the complete domain matrix is `Review All Domain Status` (`9031`)
  under collapsed Domain Status Tracks.
- Trust `Review Recovery Action` no longer relies on `overflow:hidden`.
- Trust `Review Recovery Action` (`id=906`) omits native Grafana title chrome
  (`bioetlDisplayTitle`) and keeps a one-line 16px rail so `gridPos.h=2`
  does not internally scroll (`DASH-FIT-004`). Caveats stay in the description.
- Trust authored HTML uses inline copy roles: numbered bold dashboard names,
  italic panel titles, CAPS status/scope, `<code>` 16px fields, regular 16px
  body (`design-system.md` §9.1).
- Pipeline Diagnostics no longer treats SCRAPING as proof of delivery health.

## Operator readability gate (2026-08-17)

- Required check on every `grafana/dashboards/**` change:
  `pytest tests/integration/test_dashboard_operator_readability.py`.
- Covers inline copy roles (design-system §9.1), operator clock
  `YYYY-MM-DD HH:MM` (`time:YYYY-MM-DD HH:mm`), and first-window no-scroll
  declarations. Wired in CI Tests and the `check-dashboard-operator-readability`
  pre-push hook.

## Dashboard clock format (2026-08-17)

- Operator-facing date/time on shipped dashboards is `YYYY-MM-DD HH:mm`
  (Grafana custom unit `time:YYYY-MM-DD HH:mm`; `mm` is minutes).
- Run Explorer `Completed` columns convert ISO `completed_at` strings to
  a time field, then apply that unit. DQ `Inspect Latest Successful Data`
  uses the same unit. Grafana `GF_DATE_FORMATS_*` in
  `docker-compose.monitoring.yml` applies the same pattern to the time
  picker and timeseries axes.
- Do not use `dateTimeAsIso` (ISO-8601 with `T` and offset) on operator
  panels.

## Run Explorer timestamps (2026-08-25)

- `Inspect Recent Runs` formats `started_at` / Started and `completed_at` /
  Completed with the canonical dashboard clock unit above.
- Pipeline index items also show `workflow_run_id` as Workflow run.

## Run Explorer Completed timestamp format (2026-08-05)

- `Inspect Recent Runs` formats `completed_at` / `Completed` with the
  canonical dashboard clock unit above.
- The BioETL Ops HTTP query, field value, run-selection flow, navigation, and
  empty-state semantics are unchanged.

## Selected-range description sync (2026-07-30)

- Control-plane panels backed by `$__range` now identify the selected range in
  their operator-facing descriptions.
- DQ freshness and provider status/matrix descriptions use the shared
  `TELEMETRY MISSING` fail-closed language.
- Navigation descriptions use the shared sanitizer/accessibility and
  cross-scope handoff contract across all shipped dashboards.
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

- `bioetl-control-plane-v1` (1. Trust)
- `bioetl-overview-v2` (2. Overview)
- `bioetl-runtime` (3. Pipeline Diagnostics)
- `bioetl-provider-health-v2` (4. Provider Health)
- `bioetl-dq-v2` (5. Data Quality)
- `bioetl-incident-v1` (6. Incident Workspace)
- `bioetl-run-explorer-v1` (0. Run Explorer)

**Retired (not shipped JSON):** `bioetl-workflow-overview`, `bioetl-alerts-slo`,
`bioetl-silver-reject-explorer` — use Runtime workflow band, Overview Alert/SLO
row, and CLI `bioetl quarantine inspect` respectively.

## Current shipped baseline

- All **7** shipped dashboards use `refresh: 60s` and typically
  `time.from=now-12h` (see live JSON for exact time defaults).
- Shared context shell on all 7: `$workflow`, `$pipeline`, `$run_type`,
  `$run_id`.
- `$workflow` is single-select with Include All on all shipped boards.
- `$pipeline` is single-select; `bioetl-overview-v2` intentionally defaults to
  `All`; other boards fail-close to `unknown`.
- `$run_type` is multi-select with Include All (Overview default `All`; others
  default `backfill`).
- `$run_id` is HTTP-backed identity context via
  `/ops/control-plane/filter-options`; not a Prometheus label.
- Role extensions: `$stage` (Runtime, DQ; default All), `$provider` (Provider
  Health, Incident; default unknown), hidden `$pipeline_context`/`$adapter`
  (Provider Health), hidden `$provider_hint` (Runtime).
- Forensic reject narrowing is **CLI** (`bioetl quarantine inspect`), not a
  Grafana board.

## Navigation contract now in force

- Canonical top-level bus is text navigation panel `id=1000` with links
  `0..6` only (Trust → Run Explorer).
- Dashboard-to-dashboard links use `includeVars=false` and pass only
  allowlisted `var-*` target scope.
- Same-tab navigation remains required for shipped dashboard handoff.
- **Do not** reintroduce bus adjuncts `Silver Reject Explorer`, `Explore Logs`,
  or `Explore Traces` on the default shipping surface (Loki/Tempo/Explorer
  removed 2026-07-23).
- The current dashboard remains visible as a disabled theme-safe item; the bus
  preserves contrast in dark/light themes.

## First-screen / panel-title updates

- `bioetl-overview-v2` canonical CTA panel title = `First Action`
  (`id=215`).
- ~~`bioetl-workflow-overview`~~ (**retired**): historically used `First Action`
  (`id=9`) as first-screen handoff CTA.
- Workflow selected-range evidence lives on `bioetl-runtime` workflow band:
  `Track Failed Workflow Runs`, `Track Failed Workflow Steps` (PromQL must not
  mask absence with `or vector(0)`).
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
- `bioetl-incident-v1`: triage panels under shared shell + `$provider`
- `bioetl-run-explorer-v1`: Inspect Recent Runs + canonical ID/Processed hub
- ~~`bioetl-workflow-overview`~~ (**retired** — historical panel ids only)

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

## 2026-09-16 — persisted Selected Run

Six domains use saved exact-run evidence; CURRENT remains separate. See the
UX check `docs/reports/dashboard-ux-checks/2026-09-16.md` for observed checks
and open boundaries.

## CURRENT scope explanation — 2026-09-25

Overview and Incident Workspace identify one worst workflow and domain beside
the CURRENT verdict. Run ID does not filter this card; the selected-run tables
remain persisted historical evidence. A workflow-wide failure can affect its
planned pipeline scope even when that step was skipped, and must not be read as
a failure of the selected pipeline run. Tied worst domains may exist.

Click the card to inspect the responsible workflow and gateway publication time.
The metric does not expose the exception message: Reason unavailable is honest,
and the stored workflow/pipeline reports provide the detailed failure. Critical
workflow actions rank above DQ warnings and route to current workflow evidence.

Validation receipt: `docs/reports/dashboard-ux-checks/2026-09-25.md`.

## Global alert pipeline labels

The compact and full Incident Workspace alert tables use English presentation
labels: N/A — Docker infrastructure for BioETLDockerRuntimeProbeMissing without
a pipeline label, and Not provided for other missing pipeline attributes. Real
pipeline labels, severity and FIRING/PENDING states are preserved. Alert names
link to the Docker stability runbook for that alert and the incident response
runbook otherwise; pipeline presentation labels are not navigation filters.

Live Prometheus query verified Docker, generic missing-pipeline, and real-pipeline
rows. Required readability/no-scroll checks passed. The broader state-followup
test has an unrelated Overview idempotence failure.

## Provider attribution in global alerts

Missing alert providers are enriched from positive bioetl_workflow_pipeline_expected
series only when exactly one distinct provider exists for the pipeline. Explicit
alert providers take precedence. Ambiguous or absent mappings remain Not provided.
The Docker runtime probe without a pipeline/provider uses N/A — Infrastructure.
Provider identifiers remain unchanged; chembl is displayed as ChEMBL.

Promtool verified five cases: explicit provider, unique mapping, missing mapping,
ambiguous mapping and infrastructure. The live query preserved all seven alert
rows and their severity/state. Required readability/no-scroll checks: 19 passed.


## Runtime completeness and monitoring quality

Pipeline Diagnostics separates pipeline evidence completeness from monitoring
quality. Historical rule failures or missed evaluations no longer force a
complete pipeline to INCOMPLETE for the remainder of the ten-minute window.
Monitor Coverage exposes these warnings as Monitoring quality (10m): DEGRADED.
Missing stage evidence, invalid/missing publication and missing pipeline metrics
still fail closed. Endpoint SCRAPING and 100% stage presence do not prove freshness.

Regression coverage includes a recovered scheduling miss with complete stage
signals: monitoring remains degraded while pipeline status is OK. Live Prometheus
confirmed chembl_target/backfill status 0 with monitoring gap 1 after rule reload.
Rule syntax validation passed (234 rules); 63 rules-config/readability/no-scroll
checks passed. Broader metric semantics: 57 passed, one unrelated Provider Health
copy-contract failure. Full promtool has two existing provider-fixture failures
caused by additional generated infrastructure-alert rows.

Final targeted promtool runtime/recovered-rule suite: SUCCESS. Live browser
confirmed Pipeline Status OK, stage coverage 100%, and separate orange DEGRADED
monitoring quality, with all four coverage values visible without panel scrolling.
Runtime mirrors and src/bioetl were not modified; full repository tests were not run.
