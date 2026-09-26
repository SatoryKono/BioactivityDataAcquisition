# Grafana dashboard cycle-1 — refactoring plan

Status: planning artifact. Issues opened 2026-08-17 (pack
`.github/ISSUES/DASH-CYCLE-2026-08-17-ISSUE-PACK.md`). Does **not** authorize
`.env` edits, new Prometheus series, `run_id` Prom labels, first-screen
`or vector(0)`, or debt-budget / threshold increases.

| Field | Value |
| --- | --- |
| Audit | Cycle 1, 2026-08-17, seven shipped dashboards, 234 static panel rows |
| Scope | `workflow=chembl_baseline`, `pipeline=chembl_assay`, `run_type=backfill`, `run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b`, Last 12 hours EEST |
| Gate | **BLOCK** — accepted |
| This checkout | `fix/graf-trust-8935-8941` @ `47ee374527` (ancestor of / equal to `origin/main` for dashboard JSON and both gates) |
| Risk | V3 (dashboard JSON + CI gates + live stack). Not V4: no schema / retention / forensic-deadline change. |
| Companion plans | [`plan.md`](plan.md) (OBS-FILL / six-board fill), [`plan_grafana_trust_rf_audit.md`](plan_grafana_trust_rf_audit.md) (Trust / exact-run Lane A) |

This plan rebases the cycle-1 Final summary onto the current tree. It does not
re-run the live browser matrix.

## 1. Verdict on the audit

The cycle-1 method is sound and should be kept:

- Fail-closed first-screen copies on D0–D5 (`INCOMPLETE`, `UNKNOWN`,
  `RULE/SERIES GAP`, `EMPTY DOMAIN`) are **correct**. They are not health
  verdicts and must not be “fixed” to green.
- 213 `Not Verifiable` detail panels are **not failures**. Cycle 1 only
  settled first-screen + expanded Run Explorer. Visual/layout/light/200%
  certification is explicitly incomplete.
- Direct Ops HTTP counter-evidence for the exact run is the right way to
  separate backend truth from Grafana binding.
- Gate BLOCK is correct while DASH-CYCLE-001 is unrepaired and the panel-matrix
  generator is still locked to 226.

Do **not** treat cycle 1 as a license to rewrite D1–D5 PromQL or to invent
series. The first product defect is Run Explorer variable binding.

## 2. Finding rebase against this checkout

Counted on this tree (same numbers on `origin/main` for these surfaces):

| Surface | Count |
| --- | ---: |
| Shipped dashboard JSON objects (leaf + row) | **235** |
| Non-row / row | 206 / 29 |
| `dashboard-inventory.yaml` `panel_count` sum | **235** (64+27+42+35+36+13+18) |
| `EXPECTED_PANEL_COUNT` in `report_dashboard_panel_audit_matrix.py` | **226** |
| `reviewed_expression_count` in `promql_max_over_time_counter_policy.yaml` | **41** (`reviewed_on: 2026-08-17`) |
| Live reviewed `max_over_time` Counter expressions (dashboards + rules) | **41** |

Audit said 234 vs 226. Current JSON/YAML are 235 (Trust `panel_count` 64 after
GRAF-TRUST D0 work). The extra row versus the audit inventory is expected
drift, not a second defect.

| ID | Audit | Current tree | Disposition |
| --- | --- | --- | --- |
| DASH-CYCLE-001 | Run Explorer shows `SELECT RUN` / `VALID EMPTY` and literal `$pipeline` while Ops HTTP returns identity + 11 accounting rows | Still in `bioetl-run-explorer-v1.json`. URLs use `${pipeline}` / `${run_id}`; `noValue` contains uninterpolated `'$pipeline'`; Recent Runs has **no** data link that sets `var-run_id`; `$pipeline` default is Prom `unknown`; `$run_id` default is `-` | **Open. First product fix.** |
| DASH-CYCLE-002 | D0 CRIT telemetry, D2 `RULE/SERIES GAP`, dependent cards `UNKNOWN` | Fail-closed copies still correct. OBS-FILL #8927 / PR #8933 merged (`18b7c1a3e2`). Live Prometheus proof still required after health-server recreate | **Open as live publication, not a dashboard JSON rewrite.** |
| DASH-CYCLE-003 | Inventory 234 vs generator baseline 226 | YAML already matches JSON (235). Generator + `--check` still hardcode 226 | **Open. Lock generator to the live seven-UID inventory. Do not relax the gate.** |
| DASH-CYCLE-004 | 41 reviewed Counter expressions vs policy 40 | Policy and live count are both **41** | **Resolved on this tree and `origin/main`. Verify only. Do not bump.** |

GRAF-TRUST-06 (#8937) claimed inventory + `max_over_time` closeout. The policy
count was updated; the panel-matrix generator was not. That leftover is
DASH-CYCLE-003, not a reason to reopen Lane A.

## 3. Root-cause clusters (code-backed)

### C1 — Run Explorer binding (DASH-CYCLE-001)

Three independent mechanisms can produce the observed UI. WP-0 must say which
ones fired before JSON is edited.

1. **`fieldConfig.defaults.noValue` is not interpolated by Grafana.**
   Panel 3010 literally stores
   `pipeline '$pipeline'`. When the query returns empty, the operator sees the
   dollar token even if the dashboard variable is `chembl_assay`. This alone
   explains the “literal `$pipeline`” screenshot. It does **not** by itself
   explain `SELECT RUN` on identity/accounting.
2. **Selected-run panels require dashboard variables, not a table highlight.**
   Inspect Run Identity (9402) and Inspect Processed Records (9403) call

   ```
   /ops/control-plane/identity-table?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}
   /ops/observability/processed-records?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}
   ```

   Inspect Recent Runs (3010) has no `dataLinks` / click-to-set-variable on the
   `run_id` column. Description text says “Choose a row to set the run ID”,
   but the JSON does not implement that. A visually selected table row leaves
   `$run_id=-` → `SELECT RUN`. Tests in
   `tests/integration/test_grafana_render_first_remediation.py` assert
   `noValue.startswith("SELECT RUN")` for identity cards, so that empty copy
   is contractual when no run is bound.
3. **`$pipeline` is a Prometheus query variable**
   (`label_values(bioetl_overview_pipeline_run_type_universe, pipeline)`),
   default `unknown`. While DASH-CYCLE-002 holds (empty Prom universe), the
   dropdown can stay `unknown` even when the operator pasted a `run_id` or
   opened a URL with `var-pipeline=chembl_assay` that Grafana then rejected
   as not in the option list. Infinity then calls
   `pipeline-run-reports?pipeline=unknown` → valid empty. Direct Ops HTTP
   with `pipeline=chembl_assay` still succeeds. Skill
   `.codex/skills/observability-dashboard/SKILL.md` already documents this
   split: do not start from Grafana selectors; hit Ops HTTP first.

Hypothesis order for WP-0:

1. Inspect request URL still has `pipeline=unknown` or `run_id=-`.
2. Inspect request URL has the correct values but Infinity sent a literal
   `${pipeline}` / `$pipeline`.
3. Request is correct and the backend returned rows; the panel then dropped
   them in `root_selector` / transform (less likely given `SELECT RUN`).

### C2 — Telemetry coverage (DASH-CYCLE-002)

Unchanged from [`plan.md`](plan.md): publication topology (CLI process vs
scraped health-server registry). Rehydrate landed in #8933. Cycle 1 still
seeing CRIT / `RULE/SERIES GAP` means the running `bioetl` container was not
recreated from that SHA, or rehydrate has no report for the selected
pipeline. Do not add PromQL fallbacks. Do not treat UNKNOWN as a UI bug.

### C3 — Stale panel-matrix baseline (DASH-CYCLE-003)

`docs/03-guides/dashboards/contracts/dashboard-inventory.yaml` is already
lockstep with JSON (235). The failing gate is the **second** baseline:

- `scripts/engineering/qa/report_dashboard_panel_audit_matrix.py`
  `EXPECTED_PANEL_COUNT = 226`
- `tests/integration/test_dashboard_panel_audit_matrix_contract.py`
  asserts `len(rows) == subject.EXPECTED_PANEL_COUNT`

GRAF-TRUST-06 said “derive count from the seven-UID inventory; do not hide
growth.” That derivation was not implemented. The remaining work is to make
the generator read the live inventory (or set 235 from a counted list), not
to lower the gate.

### C4 — `max_over_time` policy (DASH-CYCLE-004)

Already reviewed. Current allowed families:

- `bioetl_records_processed_total`
- `bioetl_stage_records_total`
- `bioetl_dq_records_quarantined_total`
- `bioetl_silver_filter_rejections_total`

Live count = 41 = policy. If a future panel adds a 42nd expression, review
that expression; do not pre-emptively raise the count.

## 4. Work packages

```
WP-0  Capture Grafana Inspect URL/payload for D6 3010 / 9402 / 9403
  ├── WP-1  Repair Run Explorer binding + noValue copy          DASH-CYCLE-001
  ├── WP-2  Lock panel-matrix generator to live 235 inventory   DASH-CYCLE-003
  └── WP-3  Verify max_over_time 41==41 (no edit unless drift)  DASH-CYCLE-004

WP-4  Live OBS-FILL proof (recreate bioetl, Prom probes)        DASH-CYCLE-002
  └── WP-5  Cycle-2: affected D6 subset → bounded datasource
            validator → light / 200% / remaining NV panels
```

WP-1 and WP-2 may proceed in parallel after WP-0 names the binding failure.
WP-4 is independent and must not block WP-1/WP-2. WP-5 starts only after
WP-1 is re-rendered and WP-2 `--check` is green.

### WP-0 — Inspect evidence (no product edit)

Outcome: one evidence note under
`reports/observability/remediation/20260817/` that quotes the **actual**
Infinity request URL and response status for:

- Inspect Recent Runs (last 4) — panel 3010
- Inspect Run Identity — panel 9402
- Inspect Processed Records — panel 9403

Compare each to the successful direct calls already recorded in cycle-1
`exact_run_http_evidence.md`:

```
GET /ops/observability/pipeline-run-report?pipeline=chembl_assay&run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b
GET /ops/control-plane/identity-table?pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b
GET /ops/observability/processed-records?pipeline=chembl_assay&run_type=backfill&run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b
```

Also record dashboard variable values at settle (`workflow`, `pipeline`,
`run_type`, `run_id`) from the Grafana variable picker, not from the URL bar
alone.

Requires the optional monitoring stack (operator already used it for cycle 1).
Do not start it unless the operator confirms it is still up.

### WP-1 — Run Explorer binding (DASH-CYCLE-001)

Outcome: with `pipeline=chembl_assay` and
`run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b` actually bound, panels 3010 /
9402 / 9403 show the same populated rows as direct Ops HTTP. `noValue` never
renders a dollar-token. A row click on Recent Runs sets `$run_id`.

| File | Action |
| --- | --- |
| `grafana/dashboards/bioetl-run-explorer-v1.json` | Replace `noValue` strings that embed `'$pipeline'` / `'$workflow'` with static copy (pipeline name belongs in the panel description, which Grafana does interpolate in places, or omit the name). Add a field override data link on the Run column of panels 3010 and the last-20 browser: same-dashboard URL with `var-run_id=${__data.fields.run_id}` **or** the renamed field `Run` — pick the field name **after** the `organize` transform. Keep `var-pipeline` / `var-run_type` from dashboard vars. |
| same JSON, templating | If WP-0 shows `$pipeline` stuck at `unknown` while URL/`run_id` are set: add a custom/constant fallback or an Ops HTTP `filter-options?dimension=pipeline` query variable so pipeline options do not depend on the Prom universe. Do **not** put `run_id` into PromQL. Default remains fail-closed `unknown` / `-`. |
| `tests/integration/test_grafana_render_first_remediation.py` | Keep `SELECT RUN` when `$run_id=-`. Add assertions: no `noValue` contains `$pipeline` / `$workflow`; Recent Runs has a data link that writes `var-run_id`. |
| `tests/integration/test_grafana_dashboard_metric_semantics.py` | Identity / processed-records URL templates still use `${pipeline}` and `${run_id}`; no `run_id=` in PromQL. |
| `docs/03-guides/dashboards/panels/bioetl-run-explorer-v1-panels.md` | Document browse vs selected-run and the click-to-bind contract. |

Rollback: revert the single dashboard JSON; empty-state tests stay fail-closed.

Do **not** change Infinity `root_selector` or Ops HTTP handlers unless WP-0
proves the request is already correct and the payload is dropped in the panel.

### WP-2 — Panel-matrix generator (DASH-CYCLE-003)

Outcome: `--check` and the contract test pass against the live seven-UID
inventory. Growth remains visible.

| File | Action |
| --- | --- |
| `scripts/engineering/qa/report_dashboard_panel_audit_matrix.py` | Prefer deriving the expected count from `dashboard-inventory.yaml` (sum of `panel_count` for the seven shipped UIDs) **or** from `len(_collect_rows())` compared to that sum. Stop hardcoding 226. Comment must cite the YAML contract, not #8269 / 223. |
| `tests/integration/test_dashboard_panel_audit_matrix_contract.py` | Keep the fail-closed drift test. Assert the seven UIDs and unique `(uid, panel_id)`. If the constant remains, it must equal 235 **after** a counted inventory, not as a silent bump. |
| `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml` | No count change unless JSON actually changed. Already 235. |

This is a baseline lockstep, not a quality-budget increase.

### WP-3 — `max_over_time` verify-only (DASH-CYCLE-004)

No edit unless `test_all_max_over_time_counter_expressions_are_reviewed`
fails on the implementation branch. Command:

```
python -m pytest tests/integration/test_grafana_dashboard_metric_semantics.py::test_all_max_over_time_counter_expressions_are_reviewed -q
```

If it fails because a new expression appeared, review that expression in
`configs/quality/promql_max_over_time_counter_policy.yaml` and set
`reviewed_expression_count` to the reviewed list length. Do not raise the
count to “make CI green”.

### WP-4 — Live OBS-FILL proof (DASH-CYCLE-002)

Ops only. Owned by [`plan.md`](plan.md) / closed epic #8927.

1. Recreate the `bioetl` container from the SHA that contains `18b7c1a3e2`.
2. Confirm a `chembl_assay` / `backfill` run report is visible to rehydrate.
3. Probe:

   ```
   count(bioetl_pipeline_runs_total{pipeline="chembl_assay",run_type="backfill"}) > 0
   bioetl_runtime_trust_gap_status_10m == 0
   ```

4. Only then re-read D0 telemetry and D2 Metrics Coverage.

Do not rewrite D0–D5 JSON to hide CRIT / `RULE/SERIES GAP` before those
probes pass.

### WP-5 — Cycle-2 re-audit

After WP-1 render + WP-2 `--check`:

1. Re-settle D6 first-screen and expanded Selected Run Details for the same
   `run_id`.
2. Bounded Infinity/Prom datasource validator for the repaired panels only.
3. Then the unfinished visual matrix: light theme, 200% zoom, and the 213
   `Not Verifiable` panels in batches (do not require all 234 in one pass).
4. Keep `Not Verifiable` for anything still below the fold / not requested.

Use `prompt.observability.dashboard-audit-cycle` with the same selectors.

## 5. What not to do

- Issues for this wave are already open (#8944–#8948). Do not reopen #8927 or #8937.
- Do not implement on a dirty foreign worktree. Current branch is acceptable
  for WP-2 (generator only) and for WP-1 if GRAF-TRUST follow-up PR #8943
  stays scoped; otherwise cut `fix/dash-cycle1-run-explorer` from
  `origin/main`.
- Do not start D1–D5 PromQL or first-screen JSON rewrites.
- Do not map `UNKNOWN` / `INCOMPLETE` / `EMPTY DOMAIN` / `None observed` to
  healthy.
- Do not invent Prometheus series or add `run_id` labels.
- Do not raise `reviewed_expression_count`, forensic timeout, `retention_days`,
  or any quality-scorecard budget.
- Do not treat YAML 235 vs generator 226 as permission to skip `--check`.
- Do not certify the visual/layout matrix from cycle 1.

## 6. Validation

Minimum after WP-1 + WP-2:

```
python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m pytest tests/integration/test_dashboard_panel_audit_matrix_contract.py tests/integration/test_grafana_render_first_remediation.py tests/integration/test_grafana_dashboard_metric_semantics.py tests/integration/test_grafana_layout_and_metadata.py tests/integration/test_grafana_dashboard_first_screen_contract.py -q
```

Live (operator-approved monitoring):

- Grafana Inspect URLs for 3010 / 9402 / 9403 match the direct Ops HTTP
  query string (interpolated `chembl_assay` + exact `run_id`).
- Settled D6 no longer shows literal `$pipeline` or `SELECT RUN` for that run.
- WP-4 Prom probes as above.

Post-change: no `.codex` / `.junie` edits expected. Refresh
`reports/quality/module-coverage-inventory.json` only if `src/bioetl/**/*.py`
changes (not required for WP-1/WP-2).

## 7. Approval boundaries

Owner review before:

- changing the meaning of `SELECT RUN` / `VALID EMPTY` / `UNKNOWN`;
- replacing the Prom pipeline variable with an HTTP variable that defaults to
  a real pipeline (fail-closed `unknown` must remain the empty default);
- any `RunManifest` / Ops HTTP schema change (not expected here);
- creating issues or a new PR stack.

Expected debt outcome: improved (binding defect removed, generator lockstep
restored). Budgets unchanged.

## 8. GitHub issues (opened 2026-08-17)

Pack: `.github/ISSUES/DASH-CYCLE-2026-08-17-ISSUE-PACK.md`

| Code | Pri | Issue | Maps to |
| --- | --- | --- | --- |
| DASH-CYCLE-00 | meta/P1 | [#8944](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8944) | Epic |
| DASH-CYCLE-001 | P1 | [#8946](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8946) | WP-0 + WP-1 |
| DASH-CYCLE-002 | P1 | [#8947](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8947) | WP-4 (do not reopen #8927) |
| DASH-CYCLE-003 | P1 | [#8945](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8945) | WP-2 (leftover from #8937) |
| DASH-CYCLE-005 | P2 | [#8948](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8948) | WP-5 |

DASH-CYCLE-004 was **not** opened: policy and live count are both 41.

## 9. First action

WP-0. Capture Inspect URL/payload for Run Explorer panels 3010, 9402, and
9403 under the cycle-1 selectors, then implement WP-1 against that evidence.
In parallel, WP-2 can lock `EXPECTED_PANEL_COUNT` / derive it from YAML 235
without waiting for Grafana.
