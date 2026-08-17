Parent: #8944  
Depends on: #8946 (DASH-CYCLE-001) and #8945 (DASH-CYCLE-003)  
Plan: `reports/observability/remediation/20260817/plan_dashboard_cycle1.md` WP-5

## Problem

Cycle 1 settled 21 first-screen states and left **213** panels `Not Verifiable`. It did not certify light theme, 200% zoom, tables, or timeseries. After the binding fix and generator lockstep, those surfaces must be re-scored without treating remaining `Not Verifiable` as failure.

## Work

Same selectors as cycle 1: `workflow=chembl_baseline`, `pipeline=chembl_assay`, `run_type=backfill`, `run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b` (or a current successful `chembl_assay` / `backfill` run if that artifact ages out), Last 12 hours.

1. Re-settle D6 first-screen and expanded Selected Run Details.
2. Bounded Infinity/Prom datasource validator for repaired panels 3010 / 9402 / 9403 only.
3. Then a bounded visual batch: light theme, 200% zoom, and a slice of the 213 NV panels. Do **not** require all 234/235 rows in one pass.
4. Keep `Not Verifiable` for anything still below the fold / not requested.
5. Re-read D0/D2 current-state cards only after #8947 probes; do not turn residual `UNKNOWN` into a UI defect.

Use `prompt.observability.dashboard-audit-cycle`. Commit the cycle-2 registry under `reports/observability/remediation/20260817/`.

## Acceptance

- [ ] D6 3010 / 9402 / 9403 no longer show `SELECT RUN` / literal `$pipeline` for the selected run when Ops HTTP is populated
- [ ] 0 query-execution errors on the repaired subset after Grafana variable normalization
- [ ] Light + 200% batch recorded; remaining NV panels stay NV, not FAIL
- [ ] No silent 0/green substitution on observed current-state cards
- [ ] Panel-matrix `--check` still green (#8945)

## Constraints

- Do not start D1–D5 PromQL rewrites from this issue
- Do not map fail-closed `UNKNOWN` / `INCOMPLETE` / `EMPTY DOMAIN` to healthy
- No invented series; no `run_id` Prom labels; no first-screen `or vector(0)`
- No `.env` mutation; no debt-budget increase
- Monitoring only with operator approval (ADR-010)
