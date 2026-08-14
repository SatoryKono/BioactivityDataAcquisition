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

- **First window**: top-level, non-row panels whose `gridPos.y < 18`. It is the
  answer-first viewport band where area fills may encode the primary verdict.
- **Additional panel group**: a Grafana `row` and its child panels, whether the
  row is shipped collapsed or materialized for audit.
- **Data-bearing panel**: a non-row panel with at least one enabled query target
  (`targets[]`, where `hide != true`). Text, navigation, and empty containers do
  not count as data-bearing.
- **Area fill**: background severity (`colorMode=background` or
  `backgroundSolid`), table-cell `color-background`, chart/state
  `fillOpacity > 0`, a non-`none` gradient, or an authored CSS
  `background`/`background-color`.
- **Text-only color encoding**: `colorMode=value`, table-cell `color-text`,
  threshold/series line color, or neutral `auto` table cells without an area
  fill.

CSS conversion uses the browser reference ratio `1pt = 4/3px`: `12pt = 16px`;
`14pt = 18.6667px`. Render validation uses the unrounded pixel thresholds.

## 3. P0 — truth, safety, and evidence

| ID | Requirement |
| --- | --- |
| `DASH-ARCH-001` | Grafana MUST remain an optional, read-only presentation adapter. It MUST NOT become a write authority, control plane, or required local runtime dependency. |
| `DASH-PORTFOLIO-001` | The seven provisioned JSON UIDs defined by ADR-053 MUST remain authoritative rollback fallbacks until an approved cutover. |
| `DASH-DATA-001` | Dashboard queries MUST use shipped metrics, recording rules, Grafana, or BioETL Ops HTTP contracts. Invented series are forbidden. |
| `DASH-DATA-002` | `run_id`, `manifest_id`, record identifiers, hashes, and filesystem paths MUST NOT be used as Prometheus labels or label filters. Exact-run identity belongs to Ops HTTP/control-plane evidence. |
| `DASH-STATE-001` | Missing required evidence MUST remain `UNKNOWN`, `INCOMPLETE`, or an explicit error; it MUST NOT become a healthy zero. |
| `DASH-ZERO-001` | Synthetic zero is allowed only for documented zero-valid event counters. Status, cause, freshness, latency, and trust panels MUST preserve absence. |

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

- Operator-visible body text inside panels MUST be at least `12pt` (`16px`).
- Panel titles MUST be at least `14pt` (`18.6667px`; normally authored or
  rounded to `19px`).
- Text MUST wrap, reflow, or shorten instead of shrinking below the floor.
- Inline HTML/CSS sizes below the floor are forbidden in shipped JSON.
- Grafana-managed titles, Markdown, table cells, axes, and plugin-rendered text
  MUST be checked by computed-style render evidence; static JSON alone is not
  sufficient proof.

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

## 6. P2 — consistency and maintainability

| ID | Requirement |
| --- | --- |
| `DASH-META-001` | UID, title, tags, timezone, refresh, default range, schema metadata, inventory, and panel docs MUST remain synchronized. |
| `DASH-COPY-001` | Panels MUST have actionable titles, evidence-window wording where applicable, and descriptions that explain meaning and empty-state behavior. |
| `DASH-QUERY-001` | Exact and near-duplicate PromQL MUST be consolidated or explicitly justified by role. |
| `DASH-PERF-001` | First-load query, expression-length, HTTP, refresh, panel-count, and navigation budgets MUST not regress. |
| `DASH-RENDER-001` | Release evidence MUST distinguish healthy, valid-empty, telemetry-absent, explicit-error, incomplete, loading, and blank terminal states. |

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

Static tests prove repository structure. They do not replace live datasource,
render, or human usability evidence.
