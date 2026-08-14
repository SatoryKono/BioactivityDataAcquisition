# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace. First paint is identity + processed records only (Ops HTTP
performance budget). Deeper `pipeline_run_report_v1` sections live under a
collapsed progressive-disclosure row. `run_id` is never a Prometheus label.

## Key Panels

### 1. Navigate Dashboards
- **Type:** Text
- **Purpose:** Portfolio bus handoffs with preserved time range and vars.
- **Data sources:** Static HTML + panel links.

### 2. Understand Run Scope
- **Type:** Text
- **Purpose:** Explain browse and selected-run modes, the HTTP-only run_id contract, and where full artifact paths lead.
- **Data sources:** Dashboard variables and operator copy.

### 3. Inspect Run Identity
- **Type:** Table
- **Purpose:** Run/manifest identity for selected scope (first paint). Before a
  concrete selection the returned rows request an exact Run ID; after selection
  an empty section is `VALID EMPTY`, while datasource/backend failure renders
  as `QUERY ERROR`.
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).

### 4. Inspect Processed Records
- **Type:** Table
- **Purpose:** Bronze/Silver/Gold count and denominator-explicit percentage
  accounting (first paint); the panel owns 14/24 grid columns so labels and
  values remain readable. Recorded zero, `VALID EMPTY`, and `QUERY ERROR` are
  distinct operator states.
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).

### 5. Inspect Recent Runs (last 20)
- **Type:** Table (compact first-screen index)
- **Purpose:** Last 20 pipeline-run reports for the selected pipeline; pick a
  row to set `run_id` and open exact-run identity/accounting above the fold.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
- **Layout:** Compact index; Inspect Run Identity / Processed Records stay on
  the first screen (`y<=12`). Selected-run forensics stay collapsed.
- **Empty states:** Valid empty when no matching reports exist. Backend
  unavailable when Ops HTTP cannot load the index — verify `/health/live`
  and report-root bind (`python scripts/ops/runtime/docker/verify_report_bind.py`).

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
- **Purpose:** Next-step CTA after browse or selection: verify identity and
  processed records, expand Selected Run Details, then open Trust for
  recovery/replay safety. Run Explorer is evidence-only.
- **Data sources:** Static operator copy.
