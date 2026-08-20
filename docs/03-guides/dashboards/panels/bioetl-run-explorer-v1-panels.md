# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace. First paint is browse last-4 plus identity (`3010` +
`9402`) only (Ops HTTP performance budget). Processed-records accounting and
deeper `pipeline_run_report_v1` sections live under a collapsed
progressive-disclosure row. `run_id` is never a Prometheus label.

## Key Panels

### 2. Understand Run Scope
- **Type:** Text
- **Purpose:** Explain browse and selected-run modes, the HTTP-only run_id contract, and where full artifact paths lead.
- **Data sources:** Dashboard variables and operator copy.

### 3. Inspect Run Identity
- **Type:** Table (`id=9402`)
- **Purpose:** Run/manifest identity for selected scope (first paint). Before a
  concrete selection the returned rows request an exact Run ID; after selection
  an empty section is `VALID EMPTY`, while datasource/backend failure renders
  as `QUERY ERROR`. Full identity rows remain in Selected Run Details (`3022`).
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).

### 4. Inspect Processed Records
- **Type:** Table (`id=3023`)
- **Purpose:** Bronze/Silver/Gold count and denominator-explicit percentage
  accounting inside collapsed Selected Run Details. Exact layer counts also
  exist on `pipeline_run_report_v1.layers`. Recorded zero, `VALID EMPTY`, and
  `QUERY ERROR` are distinct operator states.
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).

### 5. Inspect Recent Runs (last 4)
- **Type:** Table (compact first-screen index, `id=3010`)
- **Purpose:** Last 4 pipeline-run reports for the selected pipeline. The Run
  column data link writes `var-run_id` and `var-pipeline` from the row (Grafana
  does not bind a table highlight by itself). The complete last-20 browser
  lives in Selected Run Details (`3021`).
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
- **Layout:** Compact index; Inspect Run Identity stays on the first screen.
  Selected-run forensics stay collapsed.
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
- **Purpose:** Progressive disclosure for last-20 browse, full identity,
  processed-records accounting, funnel, reasons, reconciliation, artifacts,
  and timings.
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
  Panel links: Processed Records (`3023`).

### 11. Inspect Run Artifacts
- **Type:** Table
- **Purpose:** Artifact refs (report paths, exports) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `artifacts`

### 12. Inspect Timings & Failure
- **Type:** Text
- **Purpose:** Documents optional stage_timings/failure blocks (PARTIAL when absent; not waterfall).
- **Data sources:** Static operator copy pointing at pipeline-run-report.

## Additional shipped panels
### 16. Inspect Recent Runs (last 20)

Shipped in `grafana/dashboards/bioetl-run-explorer-v1.json` as `id=3021`.
Continuation of first-window `3010` (rows 1-4); HTTP `limit=20`.
### 17. Inspect Full Run Identity

Shipped in `grafana/dashboards/bioetl-run-explorer-v1.json` as `id=3022`.
