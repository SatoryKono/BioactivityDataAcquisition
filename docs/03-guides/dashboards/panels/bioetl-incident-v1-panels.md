# BioETL Incident Workspace - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-incident-v1.json`  
**UID:** `bioetl-incident-v1`

## Overview

Thin, platform-agnostic incident surface (Dashboard System 2.0 / DUX-08).
Reuses existing recording rules and Prometheus `ALERTS`. Not Grafana Drilldown
Investigations. Shipped JSON is source of truth.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Theme-safe workspace bus with Incident highlighted; handoffs keep time range.
- **Data sources:** Static HTML + panel links.

### 2. Provenance
- **Type:** Text
- **Purpose:** Incident scope summary (workflow/pipeline/run_type/provider filters).
- **Data sources:** Dashboard variables and operator copy.

### 3. Status
- **Type:** Stat
- **Purpose:** Worst-of L0 status for selected pipeline/run_type.
- **Data sources:** `bioetl_l0_status`

### 4. Next Best Actions
- **Type:** Text
- **Purpose:** ≤4 CTAs to Pipeline, Provider, Trust, Run Explorer with time+vars.
- **Data sources:** Static operator copy + panel links.

### 5. Ranked Suspects
- **Type:** Table
- **Purpose:** Population-first suspects from provider causes, runtime blockers, DQ reasons.
- **Data sources:** `bioetl_provider_current_cause`, `bioetl_runtime_current_blocker_reason`, `bioetl_dq_current_reason`

### 6. Alert / Event Timeline (range)
- **Type:** Table
- **Purpose:** Firing/pending alertname support surface (no business-logic rewrite).
- **Data sources:** Prometheus `ALERTS`
