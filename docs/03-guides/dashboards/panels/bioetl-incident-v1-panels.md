# BioETL Incident Workspace - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-incident-v1.json`  
**UID:** `bioetl-incident-v1`

## Overview

Incident Workspace (Phase-2). Domain-separated suspects and ALERTS timeline.
Reuses existing recording rules only. Not Grafana Drilldown Investigations.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Full portfolio bus 0–6; current disabled.
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
- **Purpose:** ≤4 operator steps; dashboard hops via Navigation bus (no duplicate target UIDs).
- **Data sources:** Static operator copy.

### 5. Suspects · Runtime blockers
- **Type:** Table
- **Purpose:** Ranked runtime blockers for selected scope.
- **Data sources:** `bioetl_runtime_current_blocker_reason`

### 6. Suspects · Provider causes
- **Type:** Table
- **Purpose:** Ranked provider causes (fleet population).
- **Data sources:** `bioetl_provider_current_cause`

### 7. Suspects · DQ reasons
- **Type:** Table
- **Purpose:** Ranked DQ current reasons (NOW lane).
- **Data sources:** `bioetl_dq_current_reason`

### 8. Alert / Event Timeline (range)
- **Type:** Table
- **Purpose:** Firing/pending alertname support surface.
- **Data sources:** Prometheus `ALERTS`
