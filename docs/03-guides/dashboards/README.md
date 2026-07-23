______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-17'

______________________________________________________________________

# Dashboards Docs Index

Дата сверки: **2026-07-24**
Источник истины: `grafana/dashboards/*.json` (7 shipped dashboards after
monitoring surface reduction 2026-07-23)

## Актуальные документы

- `dashboard-inventory.md` — canonical human-readable mapping between shipped
  dashboard JSON, docs, datasources и naming/versioning policy.
- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе, включая runtime adaptive-memory triage.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `v3.0/` — draft-spec ветка для следующей линии дашбордов: execution-aware template, selector-resolution mirror и `1. Overview` hybrid L0 plan.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `variable-reference.md` — человеческий contract для shipped dashboard variables: role, fallback, scope, propagation.
- `selector-architecture.md` — selector taxonomy, dashboard families, hidden handoff model и future execution-selector design.
- `dashboard-v2-updates.md` — active changelog по текущей shipped surface,
  selector/navigation contract и UX evidence links для последних JSON-изменений.
- `contracts/dashboard-inventory.yaml` — machine-readable mapping shipped dashboards к panels, data sources и contract metadata для drift detection и audibility.

Правило routing:

- `dashboard-inventory.md` — canonical human-readable shipped inventory;
- `contracts/dashboard-inventory.yaml` — machine-readable SSOT for drift
  detection and audit tooling;
- panel docs и usage guides не должны конкурировать с inventory role.

Текущий shipped surface (после reduction 2026-07-23):

- **7 dashboards**, navigation bus `0..6` only (no Silver Reject Explorer, no
  Loki/Tempo Explore adjuncts).
- Identity HTTP panels use datasource **BioETL Ops HTTP** → main health server
  `:8000` (`BIOETL_OPS_HTTP_URL`).
- Record-level quarantine forensics: CLI `bioetl quarantine inspect` (not Grafana).
- Monitoring stack is **opt-in**: `make docker-start-monitoring`.
- See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).
- Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor
  `0` to `bioetl_runtime_pipeline_run_type_universe`, GLOBAL provider handoff
  anchors `0` to `bioetl_provider_current_status`, and missing scope remains
  `UNKNOWN`.

Текущий reproducible render contract:

- Full-surface dashboard audits use the Playwright screenshot path from
  `python -m scripts.ops rerender-grafana`. The renderer accepts explicit
  `--theme dark|light`, `--width`, and `--height`, verifies actual theme and
  viewport, and records requested/actual values in `render-manifest.json`.
- Closure evidence covers every shipped dashboard at `1600px` and `1024px` in
  both dark and light themes. The `1024px` pass verifies wrapping navigation and
  non-clipped first-action/identity content.
- Shipped forensic rows are collapsed by default. Full-surface audit mode may
  expand them and materialize lazy panels before capture; ordinary first-screen
  evidence preserves the shipped collapsed state.
- Playwright classifies required non-row panels as `healthy`, `valid-empty`, or
  `explicit-error`. Blank, still-loading, and contradictory combinations such
  as an error marker plus `No data` fail capture.
- `python -m scripts.ops check-grafana-audit-preflight` must report
  `expanded-row-capture: ok`; when a screenshot directory is supplied, its
  manifest must also prove matching viewport/theme and terminal-state success.
- `python -m scripts.ops run-grafana-audit-cycle` writes independent
  `dashboard_semantic_gate` and `dashboard_render_gate` outcomes to
  `reports/observability/grafana/dashboard-release-gates.json`. Semantic
  validation runs even when Playwright or screenshot capture is unavailable;
  render validation still runs when semantic validation fails. The render-only
  preflight excludes full Prometheus readiness when render-only, so neither
  gate can mask or contaminate the other.
- Every full-cycle occurrence has one `occurrence_id`. The semantic report,
  Playwright manifest, and combined receipt must carry the same value; the
  receipt records the current commit/tree plus SHA-256 and dashboard/panel scope
  for both sources. Render scope is derived from each dashboard's
  `terminalStateValidation.panelStates`; UID-only, missing, malformed, or
  cross-occurrence sources force the affected gate to `fail` even if an
  in-process check claimed `pass`.
- Default CI runs the token-free static/fixture semantic policy and publishes
  `dashboard-semantic-policy`, including metric inventory, JSON/provisioning,
  selectors/variables, panel-contract drift, registry/runtime/docs
  bidirectionality, datasource-boundary, and no-data evidence. Live browser
  evidence is deliberately separate:
  the manual self-hosted `dashboard-render-host.yml` workflow publishes semantic
  source, render source, and combined occurrence receipt as three artifacts.
  A semantic CI failure blocks normal review; release requires both occurrence-
  bound live gates to pass on the supported host lane.
- Semantic severity is UID/panel-attributable: invalid queries block; required
  datasource/backend unavailability blocks; unreviewed empty or unknown
  results require review; zero and expected-empty pass. Any unrecognized
  classification also fails closed to explicit review. `telemetry_missing`
  passes only for explicitly reviewed DQ freshness panels `#8` and `#101`,
  where the visual contract is `UNKNOWN` rather than zero.
- Live audit polls Loki `/ready` within a governed total `15s` readiness/query
  budget and uses a maximum one-hour lookback. Runtime panels `#250/#251` use
  `query_range`, while
  instant aggregation panel `#257` uses `/query`; all three are required
  semantic evidence. Sparse Loki results are `expected_empty`; missing freshness
  samples are `telemetry_missing` and must render `UNKNOWN`, not zero.
- Normal repository-local runtime logs from `reports/logs/bioetl.log` are
  scraped with the canonical Loki label `job="bioetl"`; audit-only logs remain
  isolated under `job="bioetl-audit"`.
- Grafana Render API screenshots remain acceptable for render/auth smoke
  evidence, but they do not prove panel terminal states.
- On Linux, `setup_grafana_screenshot_runtime.sh` is the canonical bootstrap
  for repo-local Playwright plus the supported headless Chromium shared
  library surface.

Текущая навигационная модель:

- `0. Control Plane`, `1. Overview`, `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `5. Workflow`, `6. Alerts & SLO` образуют единую
  numbered top-level шину `0..6`.
- На всех восьми shipped dashboards navigation panel `id=1000` визуально
  показывает bus `0..6`, затем `Silver Reject Explorer`, `Explore Logs` и
  `Explore Traces`; текущий dashboard рендерится как disabled high-contrast
  item, а machine-readable `panel.links` сохраняют omit-self contract.
- Каноническая shipped surface этой шины — text navigation panel `id=1000`;
  root `dashboard.links[]` не обязаны дублировать те же handoff в header row
  рядом с Grafana variables.
- Любые дублирующие dashboard-to-dashboard ссылки из одного dashboard в один
  target dashboard запрещены: переход должен быть ровно один.
- Navigation uses theme-safe solid foreground/background tokens, visible
  hover/focus states and `flex-wrap: wrap`. At `1024px` links wrap into readable
  rows instead of being clipped or disappearing on a light background.
- `Explore Traces` остаётся optional adjunct surface и считается доступным
  только для traced runs; если runtime использовал `NoOpTracing`, пустой Tempo
  result считается корректным поведением.
- Shipped `Explore Traces` handoff opens the explicit search-first Tempo route,
  preserves the active dashboard range via `${__from}` / `${__to}`, pins
  `var-ds=tempo`, uses
  `var-groupBy=resource.service.name`, and keeps only stable pipeline/provider
  TraceQL scope so Tempo metrics queries stay under the local limit and
  `includeAll` run-type selectors cannot collapse into an invalid empty regex.
- Navigation panel links intentionally открываются в том же окне, а не в новой
  вкладке.
- Переходы pipeline-scoped dashboards -> `3. Provider Health` сохраняют
  `pipeline_context=$pipeline`, но fail-close'ятся к `provider=unknown`; если у
  source dashboard нет adapter context, `adapter` не передаётся, а target
  dashboard раскрывает собственный fallback `All adapters`.

Текущая selector model:

- machine-readable SSOT: `contracts/selector-contracts.yaml`
- human-readable mirrors: `variable-reference.md` и `selector-architecture.md`
- shipped dashboards используют unified selector taxonomy by dashboard family,
  а не один flat universal selector list
- cross-dashboard handoffs явно передают только target-scoped `var-*`
  parameters; primary dashboard links preserve the shared
  `workflow/pipeline/run_type` shell and primary `run_id` only between
  dashboards that expose that selector.
- `bioetl-workflow-overview` additionally ships hidden exact-run handoff vars
  (`workflow_context`, `pipeline_context_exact`, `run_type_context_exact`,
  `provider_context_exact`) so selected `run_id` can narrow downstream links
  without changing the visible selector shell on the same dashboard.
- For local development, the repo also contains an optional pilot plugin under
  `grafana/plugins/bioetl-selectorshell-panel` that can auto-sync visible
  `workflow/pipeline/run_type` from an exact `run_id`; shipped dashboards do
  not require that unsigned plugin by default.

## First-screen policy header

Для всех operator dashboards действует единая policy-шапка:

- `ONE BIG QUESTION`
- current scope
- provenance summary
- availability / risk notes
- `First action`

Для shipped dashboards эта политика должна быть видима на первом экране через
scope/provenance/first-action блоки, current-status row, panel descriptions и
monitoring guide.

`bioetl-overview-v2` is the canonical L0 answer-first surface and uses the
frozen `1. Overview v3` layout as its baseline. It answers one question:
what is currently broken or degraded in BioETL, and where should the operator
drill down first? The first screen materializes provenance/scope, `Status`,
`First Action`, `ID`, and `Processed Records`, then keeps compact current-state
cards for Control Plane, Runtime, Data Quality, Provider, and Data Validation
above the side-by-side deviation-first `Inputs` and `Workflow` matrices.
`Alert/SLO Triage`, historical evidence, and diagnostics routing live in
collapsed rows immediately after that bounded first path. The alert table reads
Prometheus `ALERTS`; this is presentation-only triage and does not duplicate
alert-rule business logic in dashboard queries.

`bioetl-control-plane-v1` is the `0. Control Plane` surface. It starts with the
evidence-aware `bioetl_control_plane_current_status_trusted` headline plus
trust cards for replay safety state, checkpoint freshness, ledger/manifest
consistency, and telemetry presence for the selected pipeline scope. `OK` is
possible only when all required evidence is complete; missing or stale
checkpoint/telemetry evidence renders `INCOMPLETE`. Replay/checkpoint panels route to
`checkpoint-debugging.md`, while manifest/ledger evidence panels route to
`run-manifest-inspection.md`. **Known Blind Spots** and terminal-event
evidence live below fold in collapsed incident rows, not in the first-screen
trust block.

Control Plane keeps the shared compact `ID` shell panel (`9402`) backed by
`/ops/control-plane/identity-table`. The shell panel is a two-column summary of
run/manifest identity, Provider.Entity version, contract schema, execution
flags, replay capability and mode, checkpoint anchors, optional composite run
identity, and identity health. The deeper collapsed
`Identity evidence and remaining replay-safety signals` row uses
`/ops/control-plane/identity-evidence` for P0/P1/P2 anchors, identity gaps,
replay parentage, composite identity, checkpoint anchor comparison, and
copy-friendly full values. The HTTP rows include typed `source_type`,
`source_quality`, `drilldown_type`, and `drilldown_target` fields so operators
can route from anchors to manifest, ledger, effective config, contract,
snapshot, checkpoint, lineage, and artifact evidence without PromQL joins. This
row is the dashboard-approved place for
high-cardinality identity values; do not move those values into Prometheus
labels.

Global lookup/read-path panels stay separated in a dedicated
**Global diagnostics (non-pipeline scoped)** block and MUST remain unfiltered by
`$pipeline` / `$run_type`.

`bioetl-runtime`, `bioetl-provider-health-v2`, and `bioetl-dq-v2` are
answer-first L2 incident surfaces. Their first visible rows use canonical
current-status recording rules (`bioetl_runtime_current_status_trusted`,
`bioetl_provider_current_status`, `bioetl_dq_current_status`) plus reason/cause
tables before any selected-range evidence. Range counters, trends, raw tables,
Silver reject breakdowns, logs, and traces stay below the first-screen answer
row or in collapsed diagnostic rows. Runtime `Status` and `Runtime Status`
share the trusted rule; a scrape/rule gap forces `INCOMPLETE`, never green
`OK`. `bioetl-provider-health-v2` also exposes
`Monitor Provider Telemetry Freshness` on the first screen so missing
`bioetl_provider_current_status` samples are treated as telemetry gap, not
healthy provider state.

`bioetl-overview-v2` exposes visible `workflow`, `pipeline`, `run_type`, and
`run_id` selectors. Pipeline/run_type remain the canonical current-status
Prometheus scope; `workflow` is evidence context, and `run_id` is a
control-plane-backed identity selector preserved for HTTP `ID`/details panels.
`Silver Reject Explorer` does not own the shared `workflow/run_id` shell. It
uses bounded forensic `pipeline/run_type/reason_code/field/quarantine_run_id`
and `payload_hash` selectors. Generic primary-dashboard handoffs do not map
primary `run_id` into `quarantine_run_id`; explicit record/payload drilldowns
may use forensic selectors only when the source surface owns that evidence.

## KPI ownership (canonical vs mirrors)

Правило: KPI имеет один canonical dashboard (источник ответа) и может иметь
secondary mirrors только как локальный контекст. Mirror-карточки не должны
добавлять dashboard-to-dashboard links, если такой target уже есть в top-level
шине.

| KPI | Canonical dashboard | Secondary mirrors |
| --- | --- | --- |
| Status | `1. Overview` | trusted derivatives in `2. Runtime`, `0. Control Plane` |
| First Action | `1. Overview` | `2. Runtime`, `3. Provider Health` |
| Inputs | `1. Overview` | `2. Runtime`, `4. Data Quality`, `0. Control Plane` |
| Data Validation | `1. Overview` | `2. Runtime`, `0. Control Plane` |
| Provider | `1. Overview` | `3. Provider Health` |
| Workflow | `1. Overview` | `5. Workflow` |
| Replay Safety State | `0. Control Plane` | `1. Overview`, `2. Runtime` |
| Checkpoint Freshness Lag | `0. Control Plane` | `2. Runtime` |
| Ledger/Manifest Consistency | `0. Control Plane` | `2. Runtime` |
| Provider Health (aggregated) | `3. Provider Health` | `1. Overview`, `2. Runtime` |
| DQ Status (Silver Reject / quality posture) | `4. Data Quality` | `1. Overview`, `2. Runtime` |

### Mirror policy for KPI cards

- Secondary dashboard cards, которые дублируют canonical KPI без нового
  измерения (другая гранулярность, иной период, дополнительный action context),
  MUST быть удалены или переименованы как navigational shortcut.
- Для сохранённых mirror-карточек title/description MUST явно указывать, что
  это mirror, а не primary source of truth.
- Secondary mirror-карточки MUST NOT добавлять dashboard-to-dashboard links,
  если такой target уже доступен через top-level шину.
- Если зеркало добавляет value (например, provider-scoped breakdown), укажи это
  в description без дублирования navigation link.

## Legacy-документы

Архивные материалы перемещены в `docs/03-guides/dashboards/legacy/`.

Они могут содержать устаревшие переменные (`$run-id`, `execution`) и старые формулы.


## Regenerate and verify parity

Для регенерации инвентаризации dashboard metadata (UID/title/variables/links/tags):

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --json
```

Для проверки parity с каноническими документами (`variables-guide.md`, `monitoring-index.md`)
dashboard inventory, datasource refs и mandatory links contract:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
```

Для локального health rollup shipped dashboards:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --health-summary --json
```

Для drift check против exported/deployed snapshot directory:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --deployed-dir /path/to/grafana-exports --check --json
```

CI gate запускает эту проверку в `docs.yml` и фейлит pipeline при расхождении
канонических полей.

Для deterministic validation repo-backed Prometheus rules:

```bash
uv run python -m scripts.engineering.qa check-prometheus-rules
```

Этот command surface выполняет:

```bash
promtool check rules grafana/prometheus-rules/bioetl_observability.yml grafana/prometheus-rules/bioetl_control_plane_current_status.yml
promtool test rules grafana/prometheus-rules/tests/bioetl_observability.test.yml
```

Если локальный `promtool` не найден, команда fail-fast возвращает понятную
инструкцию. В CI используется тот же entry point с `--runner docker`.
