______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-02'

______________________________________________________________________

# Dashboards Docs Index

Дата сверки: **2026-10-02**
Источник истины: `grafana/dashboards/*.json` (five shipped dashboards after the approved ADR-053 cutover on 2026-10-02)

ADR-053 also permits an optional, read-only six-route Scenes adapter during
shadow review. The five current JSON UIDs remain authoritative and reachable. See
[Optional Scenes dual path](scenes-dual-path.md) for ownership and rollback.


## Source-bound capture acceptance

#10170 pin (no live capture): [10170-contrast-reflow-pin.md](10170-contrast-reflow-pin.md).
Static accompaniment: [10170-static-accompaniment.md](10170-static-accompaniment.md).

Keep renderer, validator, and navigation generator integration under one owner.
Use a clean committed candidate, fixed UTC `--range-from` / `--range-to`, and
explicit selectors with `python -m scripts.ops render-grafana-matrix`. The matrix
records three viewports in both themes, collapsed and expanded surfaces, and
physical 1366x768 at 100%/200% reflow. At 200%, the CSS viewport is 683x384 and DSF
is 2; the page root is not scaled with CSS. Full captures retain their original
fixed-viewport scroll tiles. Terminal readiness is checked before each PNG.

Validate provenance independently with
`python -m scripts.ops check-grafana-audit-preflight --immutable-manifest <full-set-manifest> --acceptance-scope provenance`.
Only an explicitly named immutable full-set manifest is admissible. API models
before and after capture and the browser-loaded model must match committed JSON;
main PNGs, tiles, critical closeups, pagination, and keyboard series captures are
hash-bound. Historical mismatches remain unsuitable for acceptance until their
original source/artifact identity is recovered. A layout failure does not by
itself invalidate provenance.

Assemble the separate results with
`python -m scripts.ops assess-grafana-captures <immutable-manifests...> --output-dir <new-directory> --cue-review <review.json>`.
The review records `reviewer`, `source_sha`, exact `captures` hashes, all model
`panels` by UID, and `scenarios` for normal/populated, valid zero, expected
empty/selection, and error/anomaly. Critical panel reviews need observed
`evidence_text`; unavailable scenarios stay `NOT_VERIFIABLE`. Without this review,
accessibility remains `NOT_PROVEN`. Known contrast failures block acceptance;
remaining unsupported panels retain explicit status and do not imply full WCAG
conformance. Zero measured pairs produce a null rate.

Canvas measurements preserve native draw calls and current RGBA pixel witnesses;
paint contrast is computed before raster antialiasing, whose alpha is recorded
separately. Overlapping series can be measured through native named legend
buttons using keyboard isolation, with restoration and PNG evidence. This is also
an observable route to series identity without relying on color. Re-run affected
layout acceptance whenever an accessibility fix changes geometry or typography.

## Versioning strategy (issue #8632)

| Track | Status | Where |
| --- | --- | --- |
| **Dashboard System 2.0 (stable shipped)** | `Status: active` / published | This index, `dashboard-v2-usage.md`, panel docs, `design-system.md`, `contracts/` |
| **v3.0 execution-aware draft** | `Status: draft` / non-shipping | [`v3.0/`](v3.0/README.md) |
| **DUX audit protocols** | archived | [`archive/`](./archive/README.md) |

**Current stable version:** five shipped JSON dashboards (four visible navigation chips) under
`grafana/dashboards/*.json`. Operator docs for that surface are the **v2 / System 2.0**
guides. Do not treat `v3.0/` as a shipping contract.

## Актуальные документы

### Dashboard System 2.0 (current stable shipped)

- **Normative requirements:**
  [`DASHBOARD_REQUIREMENTS.md`](../../01-requirements/DASHBOARD_REQUIREMENTS.md)
  — shipping, evidence, density, typography, palette, and render-verification
  contract. Active guides below are explanatory mirrors for that contract.
- **Phase-1 (done):** epic #6800 — first-screen surgery, full nav bus, thin Incident/Run.
- **Phase-2 residual (active):** epic #6828 — see
  `dashboard-system-2.0-phase2-residual.md` (execution SSOT). Greenfield
  «Unified Plan v2.0» is **not** executable (ADR-010 / ≤7 boards / no invent metrics).
- **DUX3 residual (2026-07-29, epic #7053):** post-DSA screenshot-audit enforcement —
  [archive/audit-protocols/dux3-residual-contracts.md](archive/audit-protocols/dux3-residual-contracts.md), inventory [archive/audit-protocols/dux3-first-screen-inventory.json](archive/audit-protocols/dux3-first-screen-inventory.json).
- **DUX4 visual enforcement (2026-07-29, epic #7088):**
  [archive/audit-protocols/dux4-title-scope-harness.md](archive/audit-protocols/dux4-title-scope-harness.md), [archive/audit-protocols/dux4-field-override-inventory.json](archive/audit-protocols/dux4-field-override-inventory.json), [archive/audit-protocols/dux4-panel-redesign-matrix.json](archive/audit-protocols/dux4-panel-redesign-matrix.json).
- Residual gap table: `reports/observability/dashboard-ux-residual-gap-2026-07-28.md`.
- `operator-ux-v2.md` — first-screen zones, prose budget, empty-state taxonomy, link standard, KPI targets.
- `verdict-ontology.md` — state×confidence×basis×next_action for all workspaces.
- `migration-map-v2.md` — current uid → target workspace; alert entry rebind.
- `library-panels-inventory.md` — logical shared chrome (nav/status/actions/matrices).
- `metrics-readiness-matrix.md` — first-screen panels vs existing recording rules (no invented series).
- `usability-baseline-protocol.md` — stopwatch protocol for S1–S6.
- Baseline report: `reports/observability/usability-baseline.md`.

### Inventory and usage

- `dashboard-inventory.md` — canonical human-readable mapping between shipped
  dashboard JSON, docs, datasources и naming/versioning policy.
- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе, включая runtime adaptive-memory triage.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `v3.0/` — draft-spec ветка; first-screen surgery for 2.0 supersedes prose-first patterns where they conflict.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `variable-reference.md` — человеческий contract для shipped dashboard variables: role, fallback, scope, propagation.
- `selector-architecture.md` — selector taxonomy, dashboard families, hidden handoff model и future execution-selector design.
- `dashboard-v2-updates.md` — active changelog по текущей shipped surface,
  selector/navigation contract и UX evidence links для последних JSON-изменений.
- `contracts/dashboard-inventory.yaml` — machine-readable mapping shipped dashboards к panels, data sources и contract metadata для drift detection и audibility.
- `contracts/layout-budgets.yaml` — named fold constants (`FIRST_WINDOW_Y` vs
  `FIRST_LOAD_Y_MAX`), min-heights, first-window row caps, containment
  tolerance, answer-panel map, and governed allowlists.

Правило routing:

- `dashboard-inventory.md` — canonical human-readable shipped inventory;
- `contracts/dashboard-inventory.yaml` — machine-readable SSOT for drift
  detection and audit tooling;
- panel docs и usage guides не должны конкурировать с inventory role.

Текущий shipped surface (Dashboard System 2.0 / 2026-10-02):

- **Five dashboards**: Replay Readiness (`bioetl-control-plane-v1`), Run Overview
  (`bioetl-overview-v2`), Data Quality (`bioetl-dq-v2`), Incident Workspace
  (`bioetl-incident-v1`), Run Explorer (`bioetl-run-explorer-v1`).
- Standalone Runtime and Provider Health UIDs are retired. Saved provider checks
  belong to Run Overview panel 9480; fleet/range runtime telemetry belongs to
  Incident Workspace's collapsed Fleet diagnostics row 8808.
- Four visible navigation chips: Run Explorer, Replay Readiness, Run Overview,
  `6. Incident Workspace`. Data Quality is reached through contextual links.
- Identity HTTP panels use datasource **BioETL Ops HTTP** → main health server
  `:8000`. `BIOETL_OPS_HTTP_URL` is the Grafana-server-to-backend URL and may
  legitimately contain Docker or host-specific addressing.
- Browser-facing Ops HTTP health CTAs never expose that backend hostname. They
  use the same-origin Grafana datasource proxy
  `/api/datasources/proxy/uid/bioetl-ops-http/health/live`, so the links remain
  portable across Docker, WSL, remote hosts, and production ingress.
- Record-level quarantine forensics: CLI `bioetl quarantine inspect` (not Grafana).
- Monitoring stack is **opt-in**: `make docker-start-monitoring`.
- See [monitoring-surface-reduction](../../05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md).
- Runtime zero-count cards fail closed: selected pipeline/run_type cards anchor
  `0` to `bioetl_runtime_pipeline_run_type_universe`, GLOBAL provider handoff
  anchors `0` to `bioetl_provider_current_status`, and missing scope remains
  `UNKNOWN`.

Historical `6. Alerts & SLO` is migration terminology only; the current slot 6
is `Run Explorer` and alert triage lives in Incident Workspace.

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
  The canonical `render-manifest.json` must be byte-identical to its immutable
  `render-manifest--<full-set|selected-subset>--<capture_id>.json` occurrence
  file. Preflight rejects an extra/missing PNG, a file-count mismatch, reused
  capture IDs, source JSON SHA/version drift, missing commit SHA, or absent
  time-range/variable/row-state provenance.
- `python -m scripts.ops run-grafana-audit-cycle` writes independent
  `dashboard_semantic_gate` and `dashboard_render_gate` outcomes to
  `reports/observability/grafana/dashboard-release-gates.json`. Semantic
  validation runs even when Playwright or screenshot capture is unavailable;
  render validation still runs when semantic validation fails. The render-only
  preflight excludes full Prometheus readiness when render-only, so neither
  gate can mask or contaminate the other.
- RF-005 adds a separate [regression acceptance](regression-acceptance.md) mode
  with immutable baseline/candidate references and reviewed evidence for every
  mandatory gate. Semantic/render success alone does not close #10185 or #10171.
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
- Log/trace Explore audits against Loki/Tempo are **not** part of the shipping
  surface (removed 2026-07-23). Prefer Prometheus panel semantics and file logs
  under `reports/logs/`. Sparse/missing Prom series stay `telemetry_missing` /
  `UNKNOWN`, not silent healthy zero, unless a panel is an explicit zero-event counter.
- Grafana Render API screenshots remain acceptable for render/auth smoke
  evidence, but they do not prove panel terminal states.
- On Linux, `setup_grafana_screenshot_runtime.sh` is the canonical bootstrap
  for repo-local Playwright plus the supported headless Chromium shared
  library surface.

Текущая навигационная модель:

- Navigation panel `id=1000` is generated by
  `scripts/ops/observability/grafana/render_nav_bus.py` on Replay Readiness,
  Run Overview, Data Quality and Incident Workspace. Run Explorer uses row actions
  and its selection header instead.
- The four visible chips use `h=2`, `16px` text, normal wrapping and theme-safe
  hover/focus at `1024px`. The current chip is non-interactive; machine-readable
  `panel.links` omit self. Data Quality has no current chip in this bus.
- Root `dashboard.links[]` must not duplicate the bus. Links open in the same
  window and carry only selectors owned by the target dashboard.
- Use `rerender-grafana --navigation-only --no-expand-collapsed-rows` for live
  navigation evidence. Static contract checks do not establish browser acceptance.
- Removed: Silver Reject Explorer, Explore Logs (Loki), Explore Traces (Tempo),
  standalone Pipeline Diagnostics and Provider Health. Exact record forensics use
  `bioetl quarantine inspect`; provider saved evidence opens Overview panel 9480.

Текущая selector model:

- machine-readable SSOT: `contracts/selector-contracts.yaml`
- human-readable mirrors: `variable-reference.md` и `selector-architecture.md`
- shipped dashboards используют unified selector taxonomy by dashboard family,
  а не один flat universal selector list
- cross-dashboard handoffs явно передают только target-scoped `var-*`
  parameters; primary dashboard links preserve the shared
  `workflow/pipeline/run_type` shell and primary `run_id` only between
  dashboards that expose that selector.
- ~~`bioetl-workflow-overview`~~ (**retired**) historically shipped hidden exact-run handoff vars
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

The five shipped dashboards use a compact scope/evidence header with normal
wrapping and `16px` text. Run Explorer uses `Inspect Run Selection & Evidence`
(`id=1`); the other dashboards use their scope header at the top of the page.

| Dashboard | First question | Evidence basis and first action |
| --- | --- | --- |
| Replay Readiness | Can the selected run be replayed? | Saved `replay_checks`; verdict 9422 opens exact replay checks 9423. UNKNOWN is not a pass. |
| Run Overview | What happened in the selected run? | Ops HTTP saved assessment 9002, verdict 9604, identity 9300; domain links open Replay Readiness, DQ or local Provider Evidence 9480. |
| Data Quality | What entered and left each processing stage? | Saved accounting 9403: count in, count out, percentage; missing denominator is N/A, skipped stages are omitted, recorded zeros remain visible. |
| Incident Workspace | What is wrong now and where should I investigate? | CURRENT scope status 9401; GLOBAL ranked suspects/alerts; range and fleet diagnostics stay collapsed. |
| Run Explorer | Which saved run should I inspect? | Latest ten disk-indexed runs 3010, independent of time range; row links preserve the full Run ID and open saved evidence. |

CURRENT Prometheus telemetry is distinct from saved Ops HTTP run evidence.
`run_id` is never a Prometheus label. Processing result, presentation trust and
replay readiness are distinct assessments; absent or incomplete evidence must
remain explicit UNKNOWN. Detailed manifest/checkpoint/lineage anchors belong to
Replay Readiness's lower evidence rows and retain copy-friendly full values.

Record-level quarantine forensics are **CLI/API**, not a Grafana board:
`bioetl quarantine inspect` with bounded filters (`pipeline` / `run_type` /
`reason_code` / `field` / `quarantine_run_id` / `payload_hash`). Primary
dashboard handoffs must not map primary `run_id` into `quarantine_run_id`.

## KPI ownership (canonical vs mirrors)

Правило: KPI имеет один canonical dashboard (источник ответа) и может иметь
secondary mirrors только как локальный контекст. Mirror-карточки не должны
добавлять dashboard-to-dashboard links, если такой target уже есть в top-level
шине.

| KPI | Canonical dashboard | Secondary context |
| --- | --- | --- |
| Saved run verdict and domains | Run Overview | Run Explorer row links |
| Saved provider checks | Run Overview, panel 9480 | Incident provider triage links distinguish CURRENT from saved evidence |
| Replay readiness and checks | Replay Readiness, panels 9422/9423 | Run Overview domain link |
| Saved stage accounting | Data Quality, panel 9403 | Run Overview DQ summary |
| CURRENT incidents and range workflow evidence | Incident Workspace | Saved run links preserve identity without claiming current telemetry belongs to that run |
| Run catalog | Run Explorer | Shared navigation reset clears exact-run selection |

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

Для bounded Trust Review first-window hoist во время layout work
используется supporting helper
`scripts/ops/observability/relayout_trust_review_panels.py`.
Он не является shipped operator command; после заморозки first-screen
layout helper удаляется или складывается в governed dashboard command.
