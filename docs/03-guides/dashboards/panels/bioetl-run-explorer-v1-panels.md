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
- **Purpose:** Run/manifest identity for selected scope (first paint).
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).

### 4. Inspect Processed Records
- **Type:** Table
- **Purpose:** Bronze/Silver/Gold stage/outcome accounting (first paint).
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).

### 5. Selected Run Details
- **Type:** Row (collapsed by default)
- **Purpose:** Progressive disclosure for recent runs, funnel, reasons, reconciliation, artifacts, timings, CTA.
- **Data sources:** Nested panels below.

Nested titles (must match JSON):

### 6. Browse Recent Runs
- **Type:** Table (first-screen empty-selection utility)
- **Purpose:** Index of recent `pipeline_run_report_v1` files to pick `run_id`.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`
- **DSA-08:** Visible on first screen; selected-run forensics stay collapsed.
- **Empty state:** Browse requires written
  `reports/run-reports/pipeline/<pipeline>/<run_id>/pipeline-run-report.json`
  artifacts. HTTP `200` with `status=ok`, `count=0`, and `items=[]` means no
  artifacts exist for that pipeline; `504` with
  `contract=forensic_endpoint_error_v1` means the forensic endpoint timed out.

### 7. Inspect Stage Funnel
- **Type:** Table
- **Purpose:** Stage funnel (records_in/out, balance) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `funnel`

### 8. Inspect Top Run Reasons
- **Type:** Table
- **Purpose:** Top removal/reason codes for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reasons_top_n`

### 9. Inspect Reconciliation
- **Type:** Table
- **Purpose:** Reconciliation block from `pipeline_run_report_v1`.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reconciliation`

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
- **Purpose:** Trust / DQ / Incident / CLI forensic hops (dashboard hops via Navigation).
- **Data sources:** Static operator copy.
