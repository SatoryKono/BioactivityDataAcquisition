# Grafana / observability refactor plan — V5 (rebase of Manus V4)

Status: planning artifact only. Does **not** authorize product edits, issues,
push, merge, monitoring-stack start, `.env` mutation, or debt-budget changes.

| Field | Value |
| --- | --- |
| Supersedes | Manus V4 (10 RF packages) and the open-work reading of [`../20260817/plan_dashboard_cycle1.md`](../20260817/plan_dashboard_cycle1.md) |
| Companion (historical) | [`../20260817/plan_dashboard_cycle1.md`](../20260817/plan_dashboard_cycle1.md), [`../20260817/plan.md`](../20260817/plan.md), [`../20260817/plan_grafana_trust_rf_audit.md`](../20260817/plan_grafana_trust_rf_audit.md) |
| Evidence pin | Cycle-1 audit `89a6585` / DASH-CYCLE-001…004; WP-0 [`../20260817/wp0_run_explorer_inspect.md`](../20260817/wp0_run_explorer_inspect.md); cycle-2 [`../20260817/cycle2_re_audit.md`](../20260817/cycle2_re_audit.md) |
| Code pin | `origin/main` `9336cd7e24` (2026-08-18) |
| Landed closeout | PR [#8949](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/8949) merged; epic [#8944](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8944) and children #8945–#8948 **closed** |
| Risk of remaining work | **V3** (dashboard JSON, CI contracts, docs). Not V4 unless a residual below is explicitly upgraded (schema / retention / lineage strictness) |
| This checkout | Foreign WIP on `fix/issue-8942-s16b-config-residuals` — do not implement from that tree |

## 0. Why V4 must be rebased

Manus V4 treated four P1 findings as an open 10-package program that would
touch interface–application–infrastructure seams, Prometheus rules, and a
new telemetry-completeness projection. That reading is stale:

1. Cycle-1 issues were opened and closed the same day via #8949.
2. The cycle-1 plan already demoted DASH-CYCLE-002 from “rewrite PromQL” to
   **live publication proof**, and DASH-CYCLE-004 from “bump the count” to
   **verify-only**.
3. `origin/main` now has the product/CI pieces that V4 listed as RF-001 /
   RF-008 / RF-009 core.

V5 keeps the V4 target property and the four finding IDs, then splits each
RF into **landed / residual / out-of-scope**. Do **not** reopen #8944–#8948
or #8927 / #8937 without a fresh reproduction against `9336cd7e24`.

## 1. Target property (unchanged)

The operator UI must keep three channels distinct:

- selected **exact run** (Ops HTTP + `$run_id`);
- **current** pipeline / run-type telemetry (Prometheus, no `run_id` label);
- **Trust / replay** verdict (evidence-aware, not “run report == success”).

`success` in a run report is not replay readiness. `UNKNOWN`, `INCOMPLETE`,
`EMPTY DOMAIN`, `VALID EMPTY`, and `SELECT RUN` must not mask a selector
binding error, missing telemetry, or an endpoint failure.

## 2. Finding rebase on `origin/main` `9336cd7e24`

| ID | Audit (V4) | Current tree | Disposition |
| --- | --- | --- | --- |
| DASH-CYCLE-001 | Run Explorer shows literal `$pipeline`, `SELECT RUN`, `VALID EMPTY` while three Ops HTTP endpoints are populated | `noValue` has no `$pipeline` / `$workflow`. Panels 3010 / 3021 have Run-column links `var-run_id=${__value.raw}` + `var-pipeline` from the row. Identity/accounting still use `${pipeline}` / `${run_id}`. `$run_id=-` still `SELECT RUN` (contract). `$pipeline` is **still** a Prom `label_values(...)` variable, default `unknown` | **Core binding landed** (#8946 / #8949). **Residual:** Prom-universe dependency on first paint / URL option list (WP-0 mechanism 3, explicitly left unchanged) |
| DASH-CYCLE-002 | Trust CRIT telemetry, Diagnostics `RULE/SERIES GAP`, dependents `UNKNOWN` | Cycle-2 probes after `bioetl` recreate: `count(bioetl_pipeline_runs_total{pipeline="chembl_assay",run_type="backfill"})=2`, `bioetl_runtime_trust_gap_status_10m=0`. Fail-closed copies remain correct | **Live proof landed** (#8947). **Not** a license for a new completeness projection or first-screen `or vector(0)` |
| DASH-CYCLE-003 | Inventory 234 vs generator 226 | YAML + JSON = **235**. `EXPECTED_PANEL_COUNT = expected_panel_count_from_inventory()` | **Landed** (#8945). Residual only if JSON/YAML drift |
| DASH-CYCLE-004 | Gate 41 expressions vs policy 40 | Policy `reviewed_expression_count: 41` (`reviewed_on: 2026-08-17`); allowed families unchanged | **Count lockstep landed**. **Residual:** count is still a scalar, not derived from an expression-ID registry |

Shipped inventory (do not hardcode elsewhere):

`64 + 27 + 42 + 35 + 36 + 13 + 18 = 235`.

## 3. Manus V4 package map

```
V4 RF-001 reproduction + selector contract     → LANDED (WP-0/1) + residual R-A
V4 RF-002 centralize HTTP targets / empty-state → PARTIAL (empty-state landed;
                                                  no generator / catalog)
V4 RF-003 browser/API regression matrix         → PARTIAL (static JSON tests;
                                                  no fixture generator)
V4 RF-004 bounded datasource validator          → NOT BUILT (cycle-2 was a
                                                  re-audit, not a product
                                                  validator refactor)
V4 RF-005 telemetry-completeness projection     → DEFERRED / not required
V4 RF-006 recording rules + first-screen        → DEFERRED (OBS-FILL already
                                                  landed; do not rewrite D0–D5)
V4 RF-007 Trust lineage/retention               → OUT OF SCOPE without ADR
V4 RF-008 inventory governance                  → LANDED
V4 RF-009 max_over_time review registry         → PARTIAL (41=41; no ID list)
V4 RF-010 docs + V4 closeout                    → THIS DOCUMENT (V5)
```

One RF at a time. Do not edit dashboard JSON, datasource provisioning, and
HTTP backend in the same change unless Inspect has already shown the rendered
request payload.

## 4. Residual packages (only these remain)

Do not reuse closed issue numbers. If a residual is accepted for
implementation, open a **new** issue from a fresh reproduction.

### R-A — Pipeline selector independent of Prom universe

**Why still open.** WP-0 proved `pipeline=unknown` yields `valid_empty` even
when `chembl_assay` reports exist. #8949 writes `var-pipeline` on row click
but leaves the variable source as

`label_values(bioetl_overview_pipeline_run_type_universe, pipeline)`

with default `unknown`. A first paint, a pasted URL whose value is not in the
Prom option list, or an empty universe still drops exact-run HTTP to
`pipeline=unknown`.

| File | Change if accepted |
| --- | --- |
| `grafana/dashboards/bioetl-run-explorer-v1.json` (and shared templating on D0–D5 only if the same variable is proven stuck) | Add an Ops HTTP `filter-options?dimension=pipeline` (or existing equivalent) **in addition to** the Prom universe, or a documented custom fallback. Keep fail-closed default `unknown`. Do **not** default to a real pipeline. Do **not** put `run_id` in PromQL |
| `docs/03-guides/dashboards/contracts/selector-contracts.yaml` | Document `http_exact_run` transport: sentinel `-`, selected UUID, URL encoding, and the Prom-vs-HTTP option-list split |
| `tests/integration/test_grafana_selector_contract.py` | Assert pipeline options are not Prom-only if the JSON source changes; keep `run_id` out of PromQL matchers |

Dependencies: none. Rollback: revert JSON + contract test. Completion:
Inspect URL for 3010/9402/9403 with a pasted `var-pipeline=chembl_assay`
reaches Ops HTTP as `pipeline=chembl_assay` even when Prom universe is empty.

### R-B — Canonical Run Explorer HTTP target catalog (optional)

**Why optional.** V4 RF-002 wanted a generator so 3010/9402/9403/report
targets cannot drift. Duplication remains in
`grafana/dashboards/bioetl-run-explorer-v1.json`. Empty-state copy is already
static. A generator is debt reduction, not a binding fix.

| File | Change if accepted |
| --- | --- |
| `scripts/ops/observability/grafana/` (new checked-in catalog + generator) | Materialize Infinity URLs from one selector schema; forbid hand-edited duplicate targets |
| `grafana/dashboards/bioetl-run-explorer-v1.json` | Generated output only |
| `tests/integration/test_grafana_layout_and_metadata.py` | Empty-state taxonomy: `SELECT RUN` / `VALID EMPTY` / `QUERY ERROR` / `TREE_MISSING` / `LAYOUT_UNHEALTHY`; no unexpanded `$pipeline` in `noValue` (already asserted) |

Do not introduce runtime JavaScript. Do not change
`grafana/provisioning/datasources-core/bioetl-ops-http.yml` unless Inspect
proves a plugin contract mismatch.

### R-C — Fixture-backed selector → request regression (optional CI)

**Why optional.** Static tests already lock `noValue` and data links.
V4 RF-003 wanted selected-UUID vs sentinel fixtures and a request snapshot.
Live browser is not default CI (ADR-010).

| File | Change if accepted |
| --- | --- |
| `tests/fixtures/grafana/run_explorer/` | Generated only: selected identity, processed records, empty selection, valid empty, backend error |
| `scripts/ops/observability/grafana/generate_run_explorer_fixtures.py` | Deterministic URL snapshot; no secrets / absolute hosts |
| `tests/integration/test_grafana_dashboard_first_screen_contract.py` | Selected-run first-screen for 3010 / 9402 / 9403: no literal `$` in rendered empty copy |

Missing live browser = skip + required scheduled smoke, **not** pass.

### R-D — Bounded panel datasource validator (optional product)

**Why not landed.** #8948 cycle-2 re-audited 3010/9402/9403 via proxy; it did
not extract a reusable validator. Build this only after R-A if Inspect still
shows plugin/request drift.

Scope: repaired HTTP panels only. Keep LOC/CC gates. Interfaces must not
import infrastructure.

### R-E — `max_over_time` expression-ID registry (small CI residual)

**Why still open.** V4 RF-009 asked that `reviewed_expression_count` be
**derived** from explicit expression IDs. Today the policy is still a scalar
`41` plus allowed metric families.

| File | Change if accepted |
| --- | --- |
| `configs/quality/promql_max_over_time_counter_policy.yaml` | Add a reviewed expression-ID list; count = `len(ids)` |
| `tests/integration/test_grafana_dashboard_metric_semantics.py` | Compare live expressions to the ID list, not to a magic number |

Do **not** raise the count to make CI green. A 42nd expression needs its own
review row.

### R-F — Visual / light / 200% / remaining NV (P2, unbounded)

213 cycle-1 panels stay `Not Verifiable`. Light theme and 200% zoom were
**not** run in cycle-2. This is a new audit cycle, not a refactor of the
selector stack. Use `prompt.observability.dashboard-audit-cycle`. Do not
treat leftover NV as FAIL.

### Deferred / do not schedule from this plan

| V4 item | Why deferred |
| --- | --- |
| RF-005 / RF-006 unified telemetry-completeness projection + new recording rules | DASH-CYCLE-002 is live-proven. Fail-closed `UNKNOWN` / `RULE/SERIES GAP` are correct. New rules/series need a separate OBS program, not this rebase |
| RF-007 lineage / retention / Trust evidence source | Needs ADR/RFC. Not reproduced as a product defect after #8947 |
| Terminal success semantics, `run_id` Prom labels, timeout / debt / exemption increases, `.env`, secret-bearing integrations | Hard no |
| Versioned `RunManifest` / lineage persistence strictness | Separate ADR |

## 5. Order if residuals are accepted

```
R-A  Pipeline options without Prom universe          [P1 residual]
  ├── R-B  HTTP target catalog                       [optional debt]
  ├── R-C  Fixture request matrix                    [optional CI]
  └── R-D  Bounded datasource validator              [only if Inspect still fails]

R-E  Expression-ID registry                          [small, parallel]
R-F  Cycle-3 visual / NV batch                       [P2 audit, last]
```

R-A is the only residual that can still recreate DASH-CYCLE-001 on first
paint. Everything else is governance or a new audit.

## 6. Validation (after any accepted residual)

```
python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m pytest tests/integration/test_dashboard_panel_audit_matrix_contract.py tests/integration/test_grafana_selector_contract.py tests/integration/test_grafana_render_first_remediation.py tests/integration/test_grafana_dashboard_metric_semantics.py tests/integration/test_grafana_layout_and_metadata.py tests/integration/test_grafana_dashboard_first_screen_contract.py -q
```

Live (operator-approved monitoring only, ADR-010):

- Inspect 3010 / 9402 / 9403 with empty Prom universe + pasted
  `var-pipeline=chembl_assay` + exact `run_id`;
- compare to direct Ops HTTP;
- Prom probes from cycle-2 remain the publication bar, not a JSON rewrite.

Architecture / security: no layer/DI regression; no secrets; no debt-budget
change. Refresh `reports/quality/module-coverage-inventory.json` only if
`src/bioetl/**/*.py` changes.

## 7. Rollback and approvals

Additive-first. Rollback pairs source + generated JSON/fixtures/docs. Never
reclassify missing telemetry as zero, raise a timeout, or disable a gate.

Owner approval before: changing `SELECT RUN` / `VALID EMPTY` / `UNKNOWN`
meaning; replacing the Prom pipeline variable with an HTTP variable that
defaults to a real pipeline; any `RunManifest` / Ops HTTP schema change;
starting the monitoring compose stack.

Expected debt if R-A/R-E land: improved (first-paint binding no longer depends
on Prom universe; Counter review stops using a stale scalar). Budgets
unchanged.

## 8. First action

Do **not** implement from the current dirty `#8942` checkout.

1. Confirm whether R-A is still reproducible on `origin/main` `9336cd7e24`
   with an empty Prom universe and a pasted `var-pipeline=chembl_assay`.
2. If yes, cut `fix/dash-ra-pipeline-http-options` from `origin/main` and
   implement only R-A.
3. If no (Grafana now keeps the URL value even when it is absent from Prom
   options), record VERIFIED evidence and drop R-A; then R-E is the only
   small leftover worth a PR.
