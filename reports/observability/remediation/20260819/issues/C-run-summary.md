## Problem

Exact-run truth already lives in Ops HTTP + `pipeline_run_report_v1`. Entry dashboards (Overview, Runtime, DQ, Incident) still do not share one compact selected-run projection, so operators re-interpret CURRENT Prometheus as the UUID verdict. Row links do not contractually land on a D6 panel anchor.

## Proposed solution

**C1.** Add a **thin HTTP projection** of v1 (identity, times, funnel, top reasons, reconciliation, DQ exclusions, provider summary, artifact links). Introduce `pipeline_run_report_v2` only if v1 cannot grow without a breaking change.

**C2.** One compact Selected Run Summary panel (same schema) on D1, D2, D4, D5. D0 Trust keeps its own evidence HTTP tables. Values must match D6.

**C4.** Every actionable table row opens `/d/bioetl-run-explorer-v1` with allowlisted variables and a documented panel anchor.

**C3 (P2, same epic, later PR):** D6 Recent Runs becomes one table (default 10, selectable 4/20), not parallel recent-4 / recent-20 panels.

## Scope

Ops HTTP handlers, `configs/contracts/reports/pipeline_run_report.v1.json` (or v2), Grafana JSON for D1/D2/D4/D5/D6, navigation-links allowlists.

## Alternatives considered

Five independent HTTP calls with copied column sets — rejected; one projection.

## Acceptance criteria

- [ ] One response schema covers the compact summary fields.
- [ ] D1/D2/D4/D5 summary identity/timing/funnel match D6 for the same `$run_id`.
- [ ] Missing run → VALID EMPTY / SELECT RUN, not OK.
- [ ] Row handoff preserves time + allowlisted vars; dangling `/d/` UIDs remain forbidden.
- [ ] No PromQL `run_id` label.

Parent: DASH-SCOPE epic. Test execution for fixtures/render: `#8984` `#8986`.
