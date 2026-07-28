# BioETL Incident Workspace - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-incident-v1.json`
**UID:** `bioetl-incident-v1`

## Overview

Incident Workspace (DRM residual). Read-only triage: Active Suspects by domain,
current alerts snapshot, and range alert-state history. Reuses existing recording
rules only. Not a persistent working record. Not Grafana Drilldown Investigations.

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
- **Purpose:** ≤4 operator steps; honest read-only bounds; hops via Navigation bus.
- **Data sources:** Static operator copy.

### 5. Active Suspects · Runtime
- **Type:** Table
- **Purpose:** Domain topk runtime blockers (not cross-domain ranking).
- **Data sources:** `bioetl_runtime_current_blocker_reason`

### 6. Active Suspects · Provider
- **Type:** Table
- **Purpose:** Domain topk provider causes (fleet population).
- **Data sources:** `bioetl_provider_current_cause`

### 7. Active Suspects · DQ
- **Type:** Table
- **Purpose:** Domain topk DQ current reasons (NOW lane).
- **Data sources:** `bioetl_dq_current_reason`

### 8. Current Alerts (firing/pending)
- **Type:** Table
- **Purpose:** Instant ALERTS snapshot (firing|pending). Not a range timeline.
- **Data sources:** Prometheus `ALERTS` (instant)

### 9. Alert State History (range)
- **Type:** State timeline
- **Purpose:** Range ALERTS history across the selected dashboard time range.
- **Data sources:** Prometheus `ALERTS` (range)

### 10. Impact / confidence (honest bounds)
- **Type:** Text
- **Purpose:** Qualitative impact/confidence notes; no scored ranking claims.
- **Data sources:** Static operator copy.
