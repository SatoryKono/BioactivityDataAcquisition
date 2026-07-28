# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace. First paint is identity + processed records only (Ops HTTP
performance budget). Deeper `pipeline_run_report_v1` sections live under a
collapsed progressive-disclosure row. `run_id` is never a Prometheus label.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Portfolio bus handoffs with preserved time range and vars.
- **Data sources:** Static HTML + panel links.

### 2. Run Scope
- **Type:** Text
- **Purpose:** Explicit HTTP-only run_id contract; first-paint vs expanded report path.
- **Data sources:** Dashboard variables and operator copy.

### 3. ID
- **Type:** Table
- **Purpose:** Run/manifest identity for selected scope (first paint).
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).

### 4. Processed Records
- **Type:** Table
- **Purpose:** Bronze/Silver/Gold stage/outcome accounting (first paint).
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).

### 5. Run report detail (Ops HTTP)
- **Type:** Row (collapsed by default)
- **Purpose:** Progressive disclosure for recent runs, funnel, reasons, reconciliation, artifacts, timings, CTA.
- **Data sources:** Nested panels below.

Nested titles (must match JSON):

### 6. Recent pipeline runs (no selection)
- **Type:** Table
- **Purpose:** Index of recent `pipeline_run_report_v1` files to pick `run_id`.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-reports`

### 7. Selected run · funnel stages
- **Type:** Table
- **Purpose:** Stage funnel (records_in/out, balance) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `funnel`

### 8. Selected run · top reasons
- **Type:** Table
- **Purpose:** Top removal/reason codes for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reasons_top_n`

### 9. Selected run · reconciliation
- **Type:** Table
- **Purpose:** Reconciliation block from `pipeline_run_report_v1`.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `reconciliation`

### 10. Selected run · layers (accounting)
- **Type:** Text
- **Purpose:** Points operators at Processed Records / report `layers` rollup.
- **Data sources:** Static operator copy + Ops HTTP report shape.

### 11. Selected run · artifacts
- **Type:** Table
- **Purpose:** Artifact refs (report paths, exports) for exact run.
- **Data sources:** BioETL Ops HTTP `/ops/observability/pipeline-run-report` → `artifacts`

### 12. Selected run · stage timings / failure (optional)
- **Type:** Text
- **Purpose:** Documents optional stage_timings/failure blocks (PARTIAL when absent; not waterfall).
- **Data sources:** Static operator copy pointing at pipeline-run-report.

### 13. Next actions (≤4)
- **Type:** Text
- **Purpose:** Trust / DQ / Incident / CLI forensic hops (dashboard hops via Navigation).
- **Data sources:** Static operator copy.
