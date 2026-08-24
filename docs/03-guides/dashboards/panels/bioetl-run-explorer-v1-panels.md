# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace. First paint is the last-10 browse index (`3010`) only
(Ops HTTP performance budget). Identity (`3022`) and processed-records
accounting (`3023`) live with the other `pipeline_run_report_v1` slices under a
collapsed progressive-disclosure row. Older runs are selected from the
control-plane Run ID catalog. `run_id` is never a Prometheus label.

## Key Panels

### 2. Understand Run Scope
- **Type:** Text
- **Purpose:** Explain browse and selected-run modes, the HTTP-only run_id contract, artifact Open/Copy, and the Trust handoff.
- **Data sources:** Dashboard variables and operator copy.

### 5. Inspect Recent Runs (last 10)
- **Type:** Table (compact first-screen index)
- **Purpose:** Last 10 pipeline-run reports for the selected pipeline. The Run
  column data link writes `var-run_id` and `var-pipeline` and opens Inspect
  Run Identity (`viewPanel=3022`). Older runs: pick Run ID from the catalog.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
- **Layout:** First-window table at `y=6,h=12` with `limitField=10` and
  `cellHeight=sm` so ten rows fit the fold without internal scroll. Identity
  (`3022`) and processed records (`3023`) stay collapsed under Selected Run
  Details.
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
- **Purpose:** Progressive disclosure for identity, processed-records
  accounting, funnel, reasons, reconciliation, layer accounting, artifacts,
  and timings/failure.

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
  Panel links: Processed Records (`3023`) + Trust.

### 11. Inspect Run Artifacts
- **Type:** Table
- **Purpose:** Artifact refs (report paths, exports) for exact run. Scan cells
  stay short; Open/Copy uses the `ref` field.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `artifacts`

### 12. Inspect Timings & Failure
- **Type:** Table (`id=3014`)
- **Purpose:** Optional `failure` and `stage_timings` blocks. Empty means not
  recorded — not zero duration and not proof of success.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `failure` + `stage_timings`


## Additional shipped panels
### 17. Inspect Run Identity
- **Type:** Table (`id=3022`)
- **Purpose:** Run/manifest identity for the selected run (collapsed Selected
  Run Details), including status, time bounds, duration, and tracking_coverage.
  Before a concrete selection the returned rows request an exact Run ID; after
  selection an empty section is `VALID EMPTY`, while datasource/backend failure
  renders as `QUERY ERROR`. This is the only identity table on Run Explorer.
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` plus
  `/ops/observability/pipeline-run-report` → `identity_rows` (not Prometheus).
### 18. Inspect Processed Records
- **Type:** Table (`id=3023`)
- **Purpose:** Bronze/Silver/Gold count and denominator-explicit percentage
  accounting for the selected run (collapsed Selected Run Details). Recorded
  zero, `VALID EMPTY`, and `QUERY ERROR` are distinct operator states. Exact
  layer counts also exist on `pipeline_run_report_v1.layers`. This is the only
  processed-records table on Run Explorer.
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).
