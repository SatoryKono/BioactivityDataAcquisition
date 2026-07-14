# BioETL Overview v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

## Overview

Dashboard `1. Overview` is the primary entry point for incident triage. It uses shared shell/status/ID/provenance contracts and provides a unified view across runtime, DQ, control plane, provider, and workflow surfaces. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Navigation
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Provenance
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Status
- **Type:** Stat
- **Purpose:** Current severity for the selected scope.
- **Data sources:** `bioetl_l0_status` (recording rule with label_replace for workflow pipeline mapping)

### 4. First Action
- **Type:** Table
- **Purpose:** Guide operator to next triage action based on current state.
- **Data sources:** `bioetl_l0_next_action_route` (recording rule with label_replace for workflow pipeline mapping)

### 5. Inputs
- **Type:** Table
- **Purpose:** Show the first-screen deviation-first matrix across Control Plane,
  Runtime, Provider, Data Quality, Data Validation, and Workflow.
- **Data sources:** `bioetl_l0_input_status_selected` (recording rule with label_replace for workflow pipeline mapping)

### 6. Runtime
- **Type:** Table
- **Purpose:** Show runtime status and blockers.
- **Data sources:** `bioetl_l1_runtime_blocker_status` (recording rule with label_replace for workflow pipeline mapping)

### 7. Data Quality
- **Type:** Table
- **Purpose:** Show DQ status and validation results.
- **Data sources:** `bioetl_l1_dq_status` (recording rule with label_replace for workflow pipeline mapping)

### 8. Data Validation
- **Type:** Table
- **Purpose:** Show data validation outcomes.
- **Data sources:** Aggregated from DQ recording rules

### 9. Control Plane
- **Type:** Table
- **Purpose:** Show control plane status and replay blockers.
- **Data sources:** `bioetl_l1_control_plane_current_status` (recording rule with label_replace for workflow pipeline mapping)

### 10. Provider
- **Type:** Table
- **Purpose:** Show provider health and status.
- **Data sources:** `bioetl_l1_provider_global_status` (recording rule)

### 11. Workflow
- **Type:** Table
- **Purpose:** Show workflow execution status.
- **Data sources:** `bioetl_l1_workflow_global_status` (recording rule with label_replace for workflow pipeline mapping)

### 12. L1 Historical Trends
- **Type:** Row
- **Purpose:** Collapsed row containing repeated subsystem detail and historical
  trends after the compact Inputs matrix.
- **Data sources:** `bioetl_historical_trends`

### 13. Runtime Blockers Trend
- **Type:** Timeseries
- **Purpose:** Show runtime blockers trend over time.
- **Data sources:** `bioetl_l1_runtime_blocker_status` (recording rule with label_replace for workflow pipeline mapping)

### 14. DQ Status Trend
- **Type:** Timeseries
- **Purpose:** Show DQ status trend over time.
- **Data sources:** `bioetl_l1_dq_status` (recording rule with label_replace for workflow pipeline mapping)

### 15. Gold Lifecycle Trend
- **Type:** Timeseries
- **Purpose:** Show Gold lifecycle trend over time.
- **Data sources:** `bioetl_l1_gold_lifecycle_status` (recording rule with label_replace for workflow pipeline mapping)

### 16. Range Evidence (Historical / Recent History)
- **Type:** Row
- **Purpose:** Row-based range evidence workflow.
- **Data sources:** `bioetl_range_evidence`

### 17. Historical Failures
- **Type:** Table
- **Purpose:** Show historical failure evidence.
- **Data sources:** `bioetl_historical_failures`

### 18. Recent Terminal Runs
- **Type:** Table
- **Purpose:** Show recent terminal run evidence.
- **Data sources:** `bioetl_recent_terminal_runs`

### 19. Silver Rejects + Rate
- **Type:** Stat
- **Purpose:** Show Silver reject count and rate.
- **Data sources:** `bioetl_silver_rejects`, `bioetl_silver_reject_rate`

### 20. Diagnostics & Docs (Logs / Traces / Raw Metrics)
- **Type:** Row
- **Purpose:** Row-based diagnostics workflow.
- **Data sources:** `bioetl_diagnostics`

### 21. Diagnostics Navigation
- **Type:** Text
- **Purpose:** Explain diagnostics navigation and handoffs.
- **Data sources:** Dashboard variables and operator copy.

### 22. ID
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp.
- **Data sources:** `bioetl_pipeline_runs`

### 23. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage.
- **Data sources:** `bioetl_records_processed_total`

### 24. Alert/SLO Triage
- **Type:** Row
- **Purpose:** Expanded alert/SLO evidence immediately after the first-level
  matrix. The visible `Status` and `First Action` retain the critical verdict
  and route, while this compact table exposes alert-level impact.
- **Data sources:** `bioetl_alerts`, `bioetl_slo_pressure`

### 25. Triage Alert State
- **Type:** Table
- **Purpose:** Show alert state for triage.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

## Recording Rules

This dashboard uses Prometheus recording rules to aggregate and transform raw metrics into L0 (level 0) and L1 (level 1) aggregate status metrics. These recording rules enable complex label manipulation and workflow pipeline mapping.

### L0 Recording Rules (Level 0 - Input/Status)
- `bioetl_l0_status` - Aggregate system status with workflow pipeline mapping via label_replace
- `bioetl_l0_next_action_route` - First action route with workflow pipeline mapping via label_replace
- `bioetl_l0_input_status_selected` - Input status by input type (control_plane, runtime, provider, dq, gold) with workflow pipeline mapping via label_replace

### L1 Recording Rules (Level 1 - Aggregate Status)
- `bioetl_l1_runtime_blocker_status` - Runtime blocker status with workflow pipeline mapping via label_replace
- `bioetl_l1_dq_status` - Data quality status with workflow pipeline mapping via label_replace
- `bioetl_l1_gold_lifecycle_status` - Gold lifecycle status with workflow pipeline mapping via label_replace
- `bioetl_l1_control_plane_current_status` - Control plane status with workflow pipeline mapping via label_replace
- `bioetl_l1_provider_global_status` - Provider global status
- `bioetl_l1_workflow_global_status` - Workflow global status with workflow pipeline mapping via label_replace

### Label Replace Pattern
The recording rules use complex `label_replace` expressions to map workflow pipeline names to their base pipeline names:
```promql
label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$")
```
This pattern strips the `workflow_` prefix from pipeline names to enable cross-workflow aggregation.

### Raw Metric Starting Points
Raw metric starting points for this dashboard are:
- **System Status:** `bioetl_l0_status{pipeline=~"chembl_assay",run_type=~"incremental"}`
- **First Action route:** `bioetl_l0_next_action_route{pipeline=~"chembl_assay",run_type=~"incremental"}`
- **Input Status:** `bioetl_l0_input_status_selected{pipeline=~"chembl_assay",run_type=~"incremental"}`

Exact blocker reasons live in the Control Plane, Runtime, Data Quality, Provider Health, and Workflow dashboards. Historical evidence stays in the row above.

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows stage-specific evidence where the panel owns that selector.

## Notes

- This dashboard is the primary L1 entry point for incident triage.
- It uses shared shell/status/ID/provenance contracts across all primary dashboards.
- Row-based workflows (L1 Historical Trends, Range Evidence, Diagnostics & Docs, Alert/SLO Triage) provide structured triage paths.
- The full-width `Inputs` matrix is the deviation-first subsystem summary.
  Repeated Control Plane, Runtime, Data Quality, Provider, Data Validation, and
  Workflow mirrors live in the collapsed `Diagnostics & Docs` row.
- `Alert/SLO Triage` is the intentional expanded decision-row exception. L1
  Historical Trends, Range Evidence, and Diagnostics & Docs are collapsed
  progressive disclosure.
- First Action panel provides operator guidance based on current state.
