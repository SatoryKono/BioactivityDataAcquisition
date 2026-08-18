# R-A / R-E closeout

Date: 2026-08-18. Branch: `fix/dash-ra-re-pipeline-options`.
Does **not** reopen #8944–#8948.

## R-A — pipeline options without Prom universe

`$pipeline` on all seven shipped dashboards now loads options from
`/ops/control-plane/filter-options?dimension=pipeline&response_shape=list&workflow=${workflow}`.

- Fail-closed default remains `unknown` (Overview keeps Include All / `All`).
- Backend prefixes `unknown` so the default is always in the option list.
- PromQL current-state panels still match `$pipeline` against universe metrics.
- `$run_type` stays Prom-bounded (out of R-A).

A pasted `var-pipeline=chembl_assay` is selectable whenever that pipeline exists
in the control-plane catalog, even if Prometheus has no series.

## R-E — expression-ID registry

`configs/quality/promql_max_over_time_counter_policy.yaml` now lists 41
`reviewed_expressions` IDs. `reviewed_expression_count` MUST equal
`len(reviewed_expressions)`. The semantic gate compares live IDs to that list.

## Lockstep (pre-existing drift on origin/main)

- Trust inventory `panel_count` 64 → **65** (JSON already had 65).
- Progressive-disclosure first collapsed row Y 14 → **18** (JSON already at 18).

## Not in this change

- R-B/C/D: optional HTTP target generator / fixtures / validator.
- R-F: light / 200% / remaining NV — new audit cycle, ADR-010 monitoring.
