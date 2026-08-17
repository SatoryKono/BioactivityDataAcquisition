______________________________________________________________________

Version: 1.0.0
Status: active
Class: normative
Owner: BioETL Team
Last verified: 2026-08-14

______________________________________________________________________

# BioETL Dashboard Requirements

## 1. Authority and scope

This document is the scoped normative contract for the seven shipped Grafana
dashboards in `grafana/dashboards/*.json`. It expands `RULES.md` §3.2.3 into
testable presentation requirements without replacing `RULES.md`, accepted ADRs,
or the dashboard JSON source of truth.

Precedence inside this scope:

1. `docs/00-project/RULES.md` and accepted ADRs, especially ADR-010 and ADR-053;
2. this document for dashboard presentation requirements;
3. machine-readable selector/navigation contracts under
   `docs/03-guides/dashboards/contracts/`;
4. active dashboard design and operator guides;
5. archived DUX documents, which are historical evidence only.

The current shipping surface is Dashboard System 2.0. Draft `v3.0` documents
MUST NOT be treated as shipping requirements.

## 2. Terms and measurement boundaries

- **First window** (answer fold): top-level, non-row panels whose
  `gridPos.y < FIRST_WINDOW_Y` (`18`, from
  [`layout-budgets.yaml`](../03-guides/dashboards/contracts/layout-budgets.yaml)).
  It is the answer-first viewport band where area fills may encode the primary
  verdict.
- **First-load budget window**: top-level, non-row panels whose
  `gridPos.y < FIRST_LOAD_Y_MAX` (`28`, equal to
  [`performance-budgets.yaml`](../03-guides/dashboards/contracts/performance-budgets.yaml)
  `first_screen_y_max`). It selects panels for PromQL/HTTP first-load budgets
  only. It is not the visual fold and MUST stay distinct from `FIRST_WINDOW_Y`.
- **Additional panel group**: a Grafana `row` and its child panels, whether the
  row is shipped collapsed or materialized for audit.
- **Data-bearing panel**: a non-row panel with at least one enabled query target
  (`targets[]`, where `hide != true`). Text, navigation, and empty containers do
  not count as data-bearing.
- **Area fill**: background severity (`colorMode=background` or
  `backgroundSolid`), stat sparkline `graphMode=area`, table-cell
  `color-background`, chart/state `fillOpacity > 0`, a non-`none` default or
  override gradient, or an authored CSS `background`/`background-color`.
- **Text-only color encoding**: `colorMode=value`, table-cell `color-text`,
  threshold/series line color, or neutral `auto` table cells without an area
  fill.

Authored BioETL copy uses the browser reference ratio `1pt = 4/3px`:
`12pt = 16px`; `14pt = 18.6667px`. Render validation uses the unrounded pixel
thresholds. Grafana-managed panel chrome is governed separately by the pinned
Grafana theme tokens because dashboard JSON has no supported native-title font
size option.

## 3. P0 — truth, safety, and evidence

| ID | Requirement |
| --- | --- |
| `DASH-ARCH-001` | Grafana MUST remain an optional, read-only presentation adapter. It MUST NOT become a write authority, control plane, or required local runtime dependency. |
| `DASH-PORTFOLIO-001` | The seven provisioned JSON UIDs defined by ADR-053 MUST remain authoritative rollback fallbacks until an approved cutover. |
| `DASH-DATA-001` | Dashboard queries MUST use shipped metrics, recording rules, Grafana, or BioETL Ops HTTP contracts. Invented series are forbidden. |
| `DASH-DATA-002` | `run_id`, `manifest_id`, record identifiers, hashes, and filesystem paths MUST NOT be used as Prometheus labels or label filters. Exact-run identity belongs to Ops HTTP/control-plane evidence. |
| `DASH-STATE-001` | Missing required evidence MUST remain `UNKNOWN`, `INCOMPLETE`, or an explicit error; it MUST NOT become a healthy zero. |
| `DASH-STATE-004` | Present zero, absent telemetry, endpoint unavailable, and exact-run `processing_status` MUST remain distinct from `trust_status`. Terminal processing success MUST NOT be presented as lineage closure, retention compliance, or replay readiness. |
| `DASH-ZERO-001` | Synthetic zero is allowed only for documented zero-valid event counters. Status, cause, freshness, latency, and trust panels MUST preserve absence. |
| `DASH-DATA-003` | Removed datasources MUST stay removed (ADR-010): no panel or target MUST reference a `loki`/`tempo` datasource or the `:8081` quarantine-explorer endpoint. |
| `DASH-DATA-004` | Every panel/target datasource MUST be an allowlisted identity — the Prometheus object/string, `BioETL Ops HTTP`, or the built-in Grafana datasource. Unknown UIDs and `${DS_*}` export artifacts are forbidden. |
| `DASH-SEC-001` | HTML/text panels (`options.mode=html`) MUST NOT contain executable or embedding vectors (`<script>`, `<iframe>`, `<object>`, `<embed>`, `javascript:`, inline `on*=` handlers). |
| `DASH-STATE-003` | First-screen current-status severity cards (`stat` with `colorMode=background`) MUST set `noValue` to a fail-closed `UNKNOWN…` string; contextual empty-state text (`VALID EMPTY`, `SELECT RUN`, …) belongs to non-verdict panels only. |

## 4. P1 — operator decision path

| ID | Requirement |
| --- | --- |
| `DASH-FIRST-001` | Every dashboard MUST answer one operator question through `state × confidence × basis × next_action`. |
| `DASH-FIRST-002` | Current status and first action MUST precede selected-range and forensic evidence. Forensic rows MUST ship collapsed. |
| `DASH-STATE-002` | Operator states MUST use the canonical `OK/WARN/CRIT/UNKNOWN` palette; documented trust gates MAY add `INCOMPLETE`. Color MUST NOT be the only carrier of meaning. |
| `DASH-NAV-001` | Every dashboard MUST expose the ordered `0..6` navigation bus, omit its self-link, preserve time, and pass only target-allowlisted variables. |
| `DASH-ACTION-001` | Critical operator panels MUST expose an actionable dashboard or runbook CTA without duplicate or conflicting handoffs. |
| `DASH-LAYOUT-001` | Top-level panels MUST NOT overlap or leave unexplained gaps. Additional diagnostics MUST use progressive disclosure. |

## 5. P1 — density, typography, and palette

### 5.1 Data density in additional panel groups

`REQ-DASH-001` / `DASH-DENSITY-001`:

- Every additional panel group MUST contain at least one data-bearing panel.
- Let `A(panel) = gridPos.w × gridPos.h`.
- Let `A_total` be the sum of `A(panel)` for all non-row child panels.
- Let `A_data` be the sum for data-bearing child panels.
- The area-weighted density `D_area = A_data / A_total` MUST be at least `0.60`.
- The count density `D_count = data_bearing_panels / child_panels` MUST be at
  least `0.50`.
- Zero-area panels, missing `gridPos`, and empty groups MUST fail closed.

The area-weighted score is the primary density measure because a small help
panel should not carry the same weight as a large data table. `D_count` prevents
one oversized chart from masking a prose-heavy group.

### 5.2 Typography floors

`REQ-DASH-002` / `DASH-TYPOGRAPHY-001`:

- BioETL-authored body copy inside text/navigation panels MUST be at least
  `12pt` (`16px`).
- BioETL-authored panel headings MUST be at least `14pt` (`18.6667px`;
  normally rounded to `19px`).
- Grafana-managed panel titles MUST remain at or above the pinned theme token
  baseline (`14px` in Grafana 12); other Grafana-managed panel text MUST remain
  at or above `12px`. These native surfaces MUST also pass the 200% reflow gate
  below. Global CSS overrides, sanitizer bypasses, and screenshot-only style
  injection are forbidden remedies.
- Text MUST wrap, reflow, or shorten instead of shrinking below the floor.
- Inline HTML/CSS sizes below the authored floor are forbidden in shipped JSON.
- Grafana-managed titles, Markdown, table cells, axes, and plugin-rendered text
  MUST be checked by computed-style render evidence; static JSON alone is not
  sufficient proof.

`DASH-REFLOW-001`:

- Every shipped dashboard MUST pass Dark and Light at 100% and 200% browser
  zoom for the 1366×768 physical viewport.
- The 200% browser profile MUST use a reduced CSS layout viewport plus matching
  device scale. Applying CSS `zoom` to the root document is not browser-zoom
  evidence because it magnifies the desktop layout without reflow.
- No profile may introduce page-level horizontal overflow, clipped titles,
  filters, KPIs or table headers, and controls MUST remain usable.

### 5.3 Palette and area fills

`REQ-DASH-003` / `DASH-COLOR-001`:

- Semantic state colors are fixed: `OK=green`, `WARN=orange`, `CRIT=red`,
  `UNKNOWN/INCOMPLETE=gray`. Navigation MAY use the approved slate/blue
  theme-safe palette from the generated navigation bus.
- Area fills are allowed only in the first window and only when paired with a
  textual state mapping.
- Additional panel groups and root panels below the first window MUST use
  text-only or line-only color encoding.
- Outside the first window, stat panels MUST use `colorMode=value`, tables MUST
  use `color-text` or neutral `auto`, chart/state `fillOpacity` MUST be `0`,
  gradients MUST be `none`, and authored text panels MUST NOT set a background.
- No exception may be added merely to preserve a legacy screenshot. A necessary
  exception requires a documented operator rationale and a contract-test change.

### 5.4 Scalar information density in additional panel groups

`REQ-DASH-004` / `DASH-DENSITY-002`:

- Scalar panel = `stat`, `gauge`, or `bargauge`. `timeseries`, `table`, `text`,
  and `row` are excluded (their value count is runtime/interpretation dependent).
- Value count is `1` for a single reduced scalar; a multi-value scalar
  (`reduceOptions.values = true`) counts its non-hidden targets.
- Scalar density `rho(surface) = Σ values / Σ (gridPos.w × gridPos.h)` over the
  scalar panels of the surface.
- First screen = root, non-row scalar panels with `gridPos.y < FIRST_WINDOW_Y`.
- For every additional panel group (a `row`) with ≥1 scalar panel:
  `rho(group) > rho(first_screen)` of the same dashboard. Deep evidence groups
  MUST pack scalars more tightly than the prominent answer-first verdicts; a large
  single-value stat buried in a drilldown is the anti-pattern this catches.
- Groups without scalar panels, and dashboards whose first screen has no scalar
  panel, are exempt (N/A). Justified exceptions use the governed `scalar_density`
  allowlist (`owner + rationale + retire_when`).
- Complementary to `DASH-DENSITY-001`: that measures data-vs-chrome area; this
  measures values-per-area for scalars. A `24×6` stat showing one `UNKNOWN` is
  "100% data" under `DASH-DENSITY-001` yet very sparse here (`ρ ≈ 0.007`).
- Enforcement is opt-in per UID via `scalar_density_enforced_uids`
  (`layout-budgets.yaml`); a dashboard is enrolled only after its scalar groups
  out-densify its first screen. Baseline survey 2026-08-14: `0. Trust` groups
  `902/901/903/904` were all below the first screen and await remediation.

## 6. P2 — consistency and maintainability

| ID | Requirement |
| --- | --- |
| `DASH-META-001` | UID, title, tags, timezone, refresh, default range, schema metadata, inventory, and panel docs MUST remain synchronized. |
| `DASH-COPY-001` | Panels MUST have actionable titles, evidence-window wording where applicable, and descriptions that explain meaning and empty-state behavior. |
| `DASH-QUERY-001` | Exact and near-duplicate PromQL MUST be consolidated or explicitly justified by role. |
| `DASH-PERF-001` | First-load query, expression-length, HTTP, refresh, panel-count, and navigation budgets MUST not regress. |
| `DASH-RENDER-001` | Release evidence MUST distinguish healthy, valid-empty, telemetry-absent, explicit-error, incomplete, loading, and blank terminal states. |
| `DASH-META-002` | Panel `id`s MUST be unique within a dashboard and the root `id` MUST be `null` (provisioning-safe import; dataLink/repeat/row-expansion integrity). |
| `DASH-LAYOUT-002` | Every panel `gridPos` MUST stay inside the 24-column grid with positive extents (`x,y >= 0`, `w,h >= 1`, `x + w <= 24`). |
| `DASH-LINK-001` | Every link URL MUST be root-relative, a canonical `github.com/SatoryKono/BioactivityDataAcquisition` URL, a `data:text/plain,` copy-handoff, or the documented local Prometheus (`http://localhost:9090/`) exception. |
| `DASH-LINK-002` | Every internal `/d/<uid>` handoff MUST resolve to a shipped dashboard uid; dangling or removed-dashboard links are forbidden. |
| `DASH-VIZ-001` | `options.reduceOptions.calcs`, when present, MUST be a non-empty list of deterministic reducers (`lastNotNull`, `last`, `min`/`max`/`mean`/`sum`, …). |
| `DASH-VIZ-002` | `panel.type` MUST be an allowlisted modern plugin type; legacy `graph` and unknown/typo plugin types are forbidden. |
| `DASH-PERF-002` | `maxDataPoints`, when set on a panel, MUST be a positive integer within `[1, 5000]`. |
| `DASH-COPY-002` | Verdict severity cards MUST carry a non-empty `description` and explicit value `mappings` (state encoding; no bare numbers). |
| `DASH-COPY-008` | Authored HTML on enrolled dashboards MUST use the five inline copy roles in design-system §9.1: numbered bold dashboard names, italic panel titles, CAPS status/scope without bold, `<code>` 16px field tokens, regular 16px body. Navigation-bus chips are exempt. |
| `DASH-TIME-001` | Operator-facing date/time MUST render as `YYYY-MM-DD HH:MM`. Grafana custom units MUST be `time:YYYY-MM-DD HH:mm` (`mm` is minutes; `MM` is months and is forbidden). HTTP ISO timestamp strings MUST use `convertFieldType` to `time` before that unit. Compose `GF_DATE_FORMATS_*` MUST use the same pattern. |

### 6.1 Geometry & purpose regression locks (added 2026-08-14)

Derived from the geometry-grounded proposal
`reports/quality/dashboard-design-fill-requirements-proposal-2026-08-14.md`. `Status` is
`enforced` (a shipped test asserts it), `pending` (needs a listed prerequisite), or
`blocked` (needs render calibration or a layout change).

| ID | Requirement | Status |
| --- | --- | --- |
| `DASH-LAYOUT-003` | Every `type:"row"` header MUST have `gridPos.h == 1`. | enforced |
| `DASH-LAYOUT-004` | Root data-bearing panels MUST meet a type-aware minimum `gridPos.h`: `table >= 5`; `timeseries`/`heatmap`/`state-timeline >= 5`; `stat`/`gauge`/`bargauge >= 3` (verdict cards SHOULD be `>= 4`); `text >= 2`. Nested children inside additional panel groups use the same floors except `table >= 4` (compact forensic tables). Exceptions live in the governed min-height allowlist. | enforced |
| `DASH-FIT-001` | Always-visible root **non-row** panels MUST have `max(y+h) <= VIEWPORT_ROWS` (`18`, calibrated to the 1366×768 first-viewport / kiosk=tv chrome using Grafana stride 38px). Collapsed row headers MAY sit on or below the fold. | enforced |
| `DASH-FIT-002` | No always-visible root panel may straddle the fold: `y < FIRST_WINDOW_Y < y+h` is forbidden unless governed-allowlisted. | enforced |
| `DASH-FIT-003` | The per-dashboard canonical answer panel (§7.1) MUST be a root, non-nested panel with `gridPos.y < FIRST_WINDOW_Y` on every dashboard. | enforced |
| `DASH-FIT-004` | Every root non-row panel with `gridPos.y < FIRST_WINDOW_Y` MUST have a recorded first-window containment result. First-window `text`, `stat`, and summary-table panels MUST fail closed when `scrollHeight > clientHeight` or `scrollWidth > clientWidth`, with only the documented browser-rounding tolerance. No first-window overflow exception may be added merely to preserve a failing layout. Horizontal scrolling is allowed only for explicitly named below-fold explorer panels. | enforced |
| `DASH-FIT-005` | Every first-window `table` MUST declare a bounded first-screen row cap in `layout-budgets.yaml` and enforce that cap in the shipped JSON (`topk`, HTTP `limit`, or a deterministic Grafana filter/limit). Full evidence stays below the fold. | enforced |
| `DASH-COPY-003` | Every non-row, non-`text`, non-shell content-panel title MUST start with a canonical action verb (design-system §3.1); parsing is colon-tolerant. | enforced |
| `DASH-COPY-004` | First-window `Monitor*` panels MUST NOT use `$__range` (`Inspect + $__range` forensic panels remain allowed; `$__interval`/fixed windows are not range). | enforced |
| `DASH-COPY-005` | Non-row content-panel titles MUST be unique within a dashboard and MUST NOT be generic placeholders. | enforced |
| `DASH-COPY-006` | First-window verdict cards (background `stat` whose mappings encode `OK` plus `WARN`/`CRIT`) MUST state `OK`/`WARN`/`CRIT`/`UNKNOWN` in the description. Documented trust gates (`0. Trust`/`2. Pipeline Diagnostics` `9401`) MUST also state `INCOMPLETE`. Presence/coverage gates without that palette are out of scope. | enforced |
| `DASH-COPY-007` | Data-typed panels MUST declare ≥1 live target (non-empty PromQL `expr` or Infinity `url`, `hide != true`). | enforced |
| `DASH-PERF-003` | The answer fold (`FIRST_WINDOW_Y=18`) and the first-load budget window (`FIRST_LOAD_Y_MAX=28`) MUST stay distinct, named constants. | enforced |
| `DASH-DENSITY-002` | Every additional panel group with ≥1 scalar panel MUST have scalar density (values / `w×h`, `stat`/`gauge`/`bargauge` only) greater than the dashboard's first-screen scalar density (§5.4). | enforced (all 7 uids in scalar_density_enforced_uids) |

Named constants and governed exception allowlists (`owner + rationale + retire_when`)
live in [`layout-budgets.yaml`](../03-guides/dashboards/contracts/layout-budgets.yaml)
and are loaded by `tests/integration/_dashboard_layout_budgets.py`.

## 7. Per-dashboard responsibility

| UID | Required answer |
| --- | --- |
| `bioetl-control-plane-v1` | Can control-plane evidence be trusted, and is replay/resume safe? |
| `bioetl-overview-v2` | What is broken or degraded now, and where should the operator go first? |
| `bioetl-runtime` | What currently blocks runtime delivery? |
| `bioetl-provider-health-v2` | Which provider is degraded/failing, and why? |
| `bioetl-dq-v2` | What is the current DQ state, its evidence scope, and first action? |
| `bioetl-incident-v1` | What is the highest-confidence active suspect? |
| `bioetl-run-explorer-v1` | Which exact run is selected, and what does its immutable evidence show? |

### 7.1 Canonical answer-panel map (`DASH-FIT-003` input)

The §7 answers map to these root first-window panels. Ids are locked by
`DASH-FIT-003` against the shipped JSON and `layout-budgets.yaml`.

| UID | Answer panel (title / id) | Notes |
| --- | --- | --- |
| `bioetl-control-plane-v1` | `Monitor Replay Readiness` (`9401`) | evidence-aware trust verdict |
| `bioetl-overview-v2` | `Monitor Fleet Health` (`214`) + `Review First Action` (`215`) | verdict + next route |
| `bioetl-runtime` | `Monitor Pipeline Status` (`9401`) | trust-gated runtime verdict |
| `bioetl-provider-health-v2` | `Monitor Fleet Severity` (`9101`) | GLOBAL provider matrix |
| `bioetl-dq-v2` | `Monitor Current DQ Status` (`9401`) | NOW-lane verdict |
| `bioetl-incident-v1` | `Inspect Ranked Suspects` (`2010`) | highest-confidence suspect matrix |
| `bioetl-run-explorer-v1` | `Inspect Run Identity` (`9402`) | `Inspect Recent Runs` (`3010`) is the empty-selection utility, not the answer |

## 8. Verification contract

| Requirement | Executable evidence |
| --- | --- |
| Density, typography, and fill policy | `tests/integration/test_dashboard_presentation_requirements.py` |
| Computed title/body font floors | `scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs` plus `check_grafana_dashboard_audit_preflight.py` and their unit tests |
| State/threshold palette | `python -m scripts.engineering.qa check-dashboard-visual-semantics` |
| Inventory and metadata | `python -m scripts.engineering.qa report-dashboard-inventory --check --json` |
| Query scope and duplication | `report-dashboard-promql-scope --check`; `report-dashboard-query-duplicates --check` |
| Performance | `python -m scripts.engineering.qa check-dashboard-performance-budgets` |
| Full release render | `python -m scripts.ops run-grafana-audit-cycle` on the supported monitoring host |
| Structural & integrity invariants (`DASH-DATA-003/004`, `DASH-SEC-001`, `DASH-STATE-003`, `DASH-META-002`, `DASH-LAYOUT-002`, `DASH-LINK-001/002`, `DASH-VIZ-001/002`, `DASH-PERF-002`, `DASH-COPY-002`) | `tests/integration/test_dashboard_structural_invariants.py` |
| Geometry & purpose regression locks (`DASH-LAYOUT-003/004`, `DASH-FIT-001/002/003/004/005`, `DASH-COPY-003/004/005/006/007`, `DASH-PERF-003`) | `tests/integration/test_dashboard_geometry_and_purpose_contracts.py` + `tests/integration/test_dashboard_first_window_containment.py` + [`layout-budgets.yaml`](../03-guides/dashboards/contracts/layout-budgets.yaml) |
| Operator readability (`DASH-COPY-008`, `DASH-TIME-001`, static `DASH-FIT-004`) | `tests/integration/test_dashboard_operator_readability.py` — required on every `grafana/dashboards/**` change |
| Scalar information density (`DASH-DENSITY-002`, §5.4) | `python -m scripts.engineering.qa report-dashboard-scalar-density --check` (survey/gate) + `tests/unit/scripts/qa/test_report_dashboard_scalar_density.py` (pure) + enforced-scope gate in `tests/integration/test_dashboard_geometry_and_purpose_contracts.py` |

Static tests prove repository structure. They do not replace live datasource,
render, or human usability evidence.
