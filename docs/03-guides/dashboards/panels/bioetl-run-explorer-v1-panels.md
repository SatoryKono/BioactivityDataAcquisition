# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace. First paint is the last-4 browse index (Ops HTTP
performance budget). Identity and processed-records accounting live with the
other `pipeline_run_report_v1` slices under a collapsed progressive-disclosure
row. `run_id` is never a Prometheus label.

## Key Panels

### 2. Understand Run Scope
- **Type:** Text
- **Purpose:** Explain browse and selected-run modes, the HTTP-only run_id contract, and where full artifact paths lead.
- **Data sources:** Dashboard variables and operator copy.

### 5. Inspect Recent Runs (last 4)
- **Type:** Table (compact first-screen index)
- **Purpose:** Last 4 pipeline-run reports for the selected pipeline. The Run
  column data link writes `var-run_id` and `var-pipeline` from the row (Grafana
  does not bind a table highlight by itself). The complete last-20 browser
  lives in Selected Run Details.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
- **Layout:** Compact first-screen index. Identity (`3022`) and processed
  records (`3023`) stay collapsed under Selected Run Details.
- **Empty states:** Valid empty (`noValue` starts with `VALID EMPTY` and must
  not embed `$pipeline` — Grafana does not interpolate `noValue`) when
  Ops HTTP `index_state=valid_empty` — no matching reports for this pipeline.
  A visible `TREE_MISSING` / `LAYOUT_UNHEALTHY` / `IDENTITY_UNHEALTHY` row is
  bind or origin failure, not a selector problem; run
  `python scripts/ops/runtime/docker/verify_report_bind.py` from the checkout
  you are viewing. Backend unavailable when Ops HTTP cannot load the index —
  verify `/health/live`.

### 14. Browse Workflow Runs
- **Type:** Row (**collapsed by default**, `id=3098`)
- **Purpose:** Optional below-fold browser for workflow-run reports; it does not
  replace the pipeline-run index or add a competing first-screen path.
- **Data sources:** Nested Ops HTTP table below.

### 15. Inspect Recent Workflow Runs (last 20)
- **Type:** Table
- **Purpose:** Last 20 workflow-run reports for the selected workflow, with the
  same valid-empty and bind/origin failure distinctions as the pipeline index.
- **Data sources:** BioETL Ops HTTP
  `/ops/observability/workflow-run-reports?workflow=${workflow}&limit=20`.

### 6. Selected Run Details
- **Type:** Row (**collapsed by default**, `id=3099`)
- **Purpose:** Progressive disclosure for funnel, reasons, reconciliation,
  layer accounting, artifacts, timings, and next-step CTA.
- **Data sources:** Nested panels below (expand row to load).

Nested titles (must match JSON):

### 7. Inspect Stage Funnel
- **Type:** Table
- **Purpose:** Stage funnel (records_in/out, balance) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `funnel`

### 8. Inspect Top Run Reasons
- **Type:** Table
- **Purpose:** Top removal/reason codes for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reasons_top_n`

### 9. Inspect Reconciliation
- **Type:** Table (`id=3015`)
- **Purpose:** Reconciliation block from `pipeline_run_report_v1`.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reconciliation`
- **Presentation:** Six canonical rows in stable silver→gold order; `value`
  column labeled **Value** (not Count) with color-text for status tokens
  (`OK`/`FAIL`/…). HTTP missing-report path returns empty shell (200), not 404.
  Panel links: Processed Records + Trust.

### 10. Inspect Layer Accounting
- **Type:** Text
- **Purpose:** Points operators at Processed Records / report `layers` rollup.
- **Data sources:** Static operator copy + Ops HTTP report shape.

### 11. Inspect Run Artifacts
- **Type:** Table
- **Purpose:** Artifact refs (report paths, exports) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `artifacts`

### 12. Inspect Timings & Failure
- **Type:** Text
- **Purpose:** Documents optional stage_timings/failure blocks (PARTIAL when absent; not waterfall).
- **Data sources:** Static operator copy pointing at pipeline-run-report.

### 13. Continue Run Investigation
- **Type:** Text
- **Purpose:** Next-step CTA after browse or selection: expand Selected Run
  Details for identity and processed records, then open Trust for
  recovery/replay safety. Run Explorer is evidence-only.
- **Data sources:** Static operator copy.

## Additional shipped panels
### 16. Inspect Recent Runs (last 20)

Shipped in `bioetl-run-explorer-v1.json`.
### 17. Inspect Full Run Identity
- **Type:** Table (`id=3022`)
- **Purpose:** Run/manifest identity for the selected run (collapsed Selected
  Run Details). Before a concrete selection the returned rows request an exact
  Run ID; after selection an empty section is `VALID EMPTY`, while
  datasource/backend failure renders as `QUERY ERROR`. This is the only
  identity table on Run Explorer (the compact first-window teaser was removed
  as a same-row subset).
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).
### 18. Inspect Full Processed Records
- **Type:** Table (`id=3023`)
- **Purpose:** Bronze/Silver/Gold count and denominator-explicit percentage
  accounting for the selected run (collapsed Selected Run Details). Recorded
  zero, `VALID EMPTY`, and `QUERY ERROR` are distinct operator states. This is
  the only processed-records table on Run Explorer (the compact first-row
  teaser was removed as a same-row subset).
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).
