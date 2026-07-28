# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`  
**UID:** `bioetl-run-explorer-v1`

## Overview

Run-centric workspace (Dashboard System 2.0 / DUX-10). Single-run identity and
processed-record accounting via **BioETL Ops HTTP**. `run_id` is never a
Prometheus label. Other boards keep a thin collapsed run-context row that points
here.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Handoffs to Trust and Overview with preserved time range and vars.
- **Data sources:** Static HTML + panel links.

### 2. Run Scope
- **Type:** Text
- **Purpose:** Explicit HTTP-only run_id contract and CLI forensic pointers.
- **Data sources:** Dashboard variables and operator copy.

### 3. ID
- **Type:** Table
- **Purpose:** Run/manifest identity for selected scope.
- **Data sources:** BioETL Ops HTTP `/ops/control-plane/identity-table` (not Prometheus).

### 4. Processed Records
- **Type:** Table
- **Purpose:** Bronze/Silver/Gold stage/outcome accounting.
- **Data sources:** BioETL Ops HTTP `/ops/observability/processed-records` (not Prometheus).

### 5. Control-plane / DQ handoffs
- **Type:** Text
- **Purpose:** Next hops for resume safety, DQ aggregates, and CLI forensics.
- **Data sources:** Static operator copy.
