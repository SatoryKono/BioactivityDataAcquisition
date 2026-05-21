# Grafana Dashboard Audit - GitHub Issue Pack (2026-05-19)

Источник findings: audit shipped dashboards against `grafana/dashboards/*.json`
and operator/dashboard documentation.

JSON SSOT reviewed:

- `grafana/dashboards/bioetl-control-plane-v1.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-provider-health-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-silver-reject-explorer.json`
- `grafana/dashboards/bioetl-workflow-overview.json`

Operator/doc surfaces reviewed:

- `docs/03-guides/dashboards/README.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/03-guides/dashboards/dashboard-v2-updates.md`
- `docs/03-guides/dashboards/dashboard-extension-llm.md`
- `docs/03-guides/dashboards/navigation-contract.md`
- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/panel-title-inventory.md`
- `docs/05-operations/01-monitoring-guide.md`
- `grafana/README.md`

Verification performed:

- `uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json`
- `uv run pytest tests/integration/test_dashboard_required_panel_links.py tests/integration/test_dashboard_panel_titles.py tests/integration/test_dashboard_panel_descriptions.py tests/integration/test_dashboard_scope_reset_tooltips.py tests/integration/test_dashboard_provider_context_mapping.py tests/integration/test_dashboard_units_decimals.py tests/integration/test_dashboard_panel_visualization_standards.py tests/unit/grafana/test_workflow_dashboard_json_valid.py tests/unit/grafana/test_silver_reject_explorer_copy.py -q`

Note:

- Live duplicate check against GitHub issues was not completed in this
  environment because `gh` is unavailable locally.

## Recommended Issue Set

### Issue 1

**Title**

`Grafana docs: formalize the Control Plane navigation exception for Explore links`

**Priority**

`P1`

**Area**

`grafana`, `docs`, `operator-navigation`

**Problem**

Current dashboard docs disagree on whether every shipped navigation panel
`id=1000` must expose `Explore Logs` and `Explore Traces`.

- `docs/03-guides/dashboards/README.md:52-54` says all shipped navigation
  panels include those adjunct links.
- `docs/03-guides/dashboards/dashboard-v2-usage.md:337-345` says the same.
- `docs/05-operations/01-monitoring-guide.md:183-185` documents an intentional
  exception for `bioetl-control-plane-v1`.
- The shipped JSON for `bioetl-control-plane-v1` omits Explore adjunct links in
  both HTML content and `panel.links`.

This leaves the canonical navigation contract ambiguous for future dashboard
edits, audits, and tests.

**Evidence**

- [`docs/03-guides/dashboards/README.md:52`](../03-guides/dashboards/README.md)
- [`docs/03-guides/dashboards/dashboard-v2-usage.md:337`](../03-guides/dashboards/dashboard-v2-usage.md)
- [`docs/05-operations/01-monitoring-guide.md:183`](../05-operations/01-monitoring-guide.md)
- [`grafana/dashboards/bioetl-control-plane-v1.json:32`](../../../grafana/dashboards/bioetl-control-plane-v1.json)
- [`grafana/dashboards/bioetl-control-plane-v1.json:38`](../../../grafana/dashboards/bioetl-control-plane-v1.json)

**Expected Outcome**

One canonical rule explicitly states whether `bioetl-control-plane-v1` is a
documented exception or whether its JSON must be brought back into the global
adjunct-link contract.

**Acceptance Criteria**

- A single canonical doc states the navigation rule for Explore adjunct links.
- Control Plane is either explicitly listed as an exception or updated to match
  the universal contract.
- Mirror docs no longer contradict each other.
- Contract/tests are updated so this ambiguity cannot silently return.

---

### Issue 2

**Title**

`Grafana runtime dashboard: make first-screen Runtime Telemetry Gap readable`

**Priority**

`P1`

**Area**

`grafana`, `dashboard-ux`, `runtime`

**Problem**

`bioetl-runtime` first-screen UX relies on `Runtime Telemetry Gap` as a trust
marker for interpreting zero-valued blocker cards, but the panel is currently
rendered with width `w=1`.

Docs position it as a first-screen datasource-trust marker:

- `dashboard-v2-usage.md:143-149` says Runtime keeps an explicit telemetry-gap
  panel first-screen.

The shipped JSON makes that panel visually tiny:

- `grafana/dashboards/bioetl-runtime.json:905-911` shows
  `gridPos.w = 1` for panel `id=9102`.

The metric semantics are sound; the discoverability is not.

**Evidence**

- [`docs/03-guides/dashboards/dashboard-v2-usage.md:143`](../03-guides/dashboards/dashboard-v2-usage.md)
- [`grafana/dashboards/bioetl-runtime.json:905`](../../../grafana/dashboards/bioetl-runtime.json)

**Expected Outcome**

The telemetry-gap signal remains first-screen and becomes legible enough to act
as an actual operator trust gate.

**Acceptance Criteria**

- Panel `id=9102` remains on the first screen.
- Its layout is widened enough to be readable without hover/inspection.
- First-screen runtime row remains non-overlapping and preserves current
  answer-first order.
- Dashboard UX artifact records the before/after effect on runtime incident
  triage.

---

### Issue 3

**Title**

`Grafana docs: replace stale dashboard-v2-updates.md with a current shipped-surface change log`

**Priority**

`P1`

**Area**

`docs`, `grafana`, `change-log`

**Problem**

`docs/03-guides/dashboards/dashboard-v2-updates.md` is materially stale and now
misstates the shipped dashboard surface.

Examples:

- It says `overview` exposes only `$pipeline` and `$run_type`.
- It says `control-plane-v1` exposes only `$pipeline` and `$run_type`.
- It says `provider-health-v2` exposes only `$provider` and `$adapter`.
- It says forensic `run_id` was removed from Prometheus-backed dashboards.

Current shipped JSON already uses the shared context shell
`$workflow/$pipeline/$run_type/$run_id` across primary dashboards.

Because the file presents itself as a verified updates/audit surface, it is now
misleading rather than helpful.

**Evidence**

- [`docs/03-guides/dashboards/dashboard-v2-updates.md:37`](../03-guides/dashboards/dashboard-v2-updates.md)
- [`docs/03-guides/dashboards/dashboard-v2-updates.md:43`](../03-guides/dashboards/dashboard-v2-updates.md)
- [`docs/03-guides/dashboards/dashboard-v2-updates.md:54`](../03-guides/dashboards/dashboard-v2-updates.md)
- [`grafana/dashboards/bioetl-overview-v2.json:3011`](../../../grafana/dashboards/bioetl-overview-v2.json)
- [`grafana/dashboards/bioetl-control-plane-v1.json:4000`](../../../grafana/dashboards/bioetl-control-plane-v1.json)
- [`grafana/dashboards/bioetl-provider-health-v2.json:2446`](../../../grafana/dashboards/bioetl-provider-health-v2.json)

**Expected Outcome**

Either:

- the file is fully refreshed to current shipped reality, or
- it is archived/replaced by a slimmer current-state change-log surface that is
  actually maintained.

**Acceptance Criteria**

- The file no longer contains stale variable-surface claims.
- It reflects the current primary dashboard shell and current panel naming.
- Stale references to removed surfaces/old IDs are removed or archived.
- The document has a clear maintenance rule or replacement path.

---

### Issue 4

**Title**

`Grafana docs: sync selector and panel-title mirrors with current JSON naming`

**Priority**

`P1`

**Area**

`docs`, `grafana`, `selectors`, `panel-contracts`

**Problem**

Several human-readable dashboard mirrors still describe old panel names or old
selector behavior:

- `variable-reference.md` still describes `$workflow` as multi-select with
  Include All on primary dashboards.
- `grafana/README.md` and `01-monitoring-guide.md` still use `Next Action` for
  Overview where shipped JSON already says `First Action`.
- `dashboard-v2-usage.md`, `panel-title-inventory.md`, and several checklist
  docs still refer to `Next Diagnostic Surface` and `Workflow Scope` on the
  workflow dashboard, while the shipped dashboard already uses `First Action`
  and `Provenance`.

This is documentation drift, not dashboard behavior drift.

**Evidence**

- [`docs/03-guides/dashboards/variable-reference.md:33`](../03-guides/dashboards/variable-reference.md)
- [`grafana/README.md:875`](../../../grafana/README.md)
- [`docs/05-operations/01-monitoring-guide.md:150`](../05-operations/01-monitoring-guide.md)
- [`docs/03-guides/dashboards/dashboard-v2-usage.md:479`](../03-guides/dashboards/dashboard-v2-usage.md)
- [`docs/03-guides/dashboards/panel-title-inventory.md:187`](../03-guides/dashboards/panel-title-inventory.md)
- [`grafana/dashboards/bioetl-overview-v2.json:243`](../../../grafana/dashboards/bioetl-overview-v2.json)
- [`grafana/dashboards/bioetl-workflow-overview.json:1099`](../../../grafana/dashboards/bioetl-workflow-overview.json)
- [`grafana/dashboards/bioetl-provider-health-v2.json:2449`](../../../grafana/dashboards/bioetl-provider-health-v2.json)

**Expected Outcome**

Human-readable docs describe the current shipped selectors and titles without
inventing alternate names.

**Acceptance Criteria**

- `$workflow` is documented as single-select everywhere it is single-select in
  shipped JSON.
- Overview docs consistently use `First Action`.
- Workflow docs no longer reference `Next Diagnostic Surface` or `Workflow Scope`
  unless clearly marked historical.
- Panel-title inventories and checklist docs align with current JSON titles.

---

### Issue 5

**Title**

`Grafana QA: add drift checks for dashboard docs beyond inventory parity`

**Priority**

`P2`

**Area**

`tests`, `docs`, `grafana`, `governance`

**Problem**

The current parity/inventory checks are strong on links, variables, titles, and
layout invariants inside JSON, but they do not catch several classes of doc
drift that surfaced in this audit:

- universal-vs-exception navigation rules in prose
- stale panel names in narrative docs
- stale selector semantics in human mirrors
- stale change-log/update pages that still claim to be verified

As a result, dashboard JSON can remain healthy while operator docs quietly
drift away from shipped behavior.

**Evidence**

- Existing inventory parity passed during this audit.
- Doc drift still remained in:
  - [`docs/03-guides/dashboards/dashboard-v2-updates.md:43`](../03-guides/dashboards/dashboard-v2-updates.md)
  - [`docs/03-guides/dashboards/README.md:52`](../03-guides/dashboards/README.md)
  - [`docs/03-guides/dashboards/variable-reference.md:33`](../03-guides/dashboards/variable-reference.md)
  - [`docs/03-guides/dashboards/panel-title-inventory.md:187`](../03-guides/dashboards/panel-title-inventory.md)

**Expected Outcome**

Repo quality gates should detect the classes of drift found in this audit
before they accumulate across several dashboard iterations.

**Acceptance Criteria**

- Add at least one automated check for stale panel-title mirrors.
- Add at least one automated check for selector-contract prose drift.
- Add a check or explicit exception registry for navigation-contract prose that
  differs by dashboard family.
- `dashboard-v2-updates.md` either enters a testable maintenance flow or is
  retired from the active documentation set.

## Suggested Issue Order

1. Issue 1
2. Issue 3
3. Issue 4
4. Issue 2
5. Issue 5

Rationale:

- first fix the canonical doc contradictions,
- then refresh stale dashboard documentation mirrors,
- then rebalance the one confirmed first-screen JSON UX weakness,
- finally harden QA so the same drift pattern does not recur.
