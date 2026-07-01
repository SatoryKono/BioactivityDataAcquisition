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
- **Data sources:** `bioetl_current_status`

### 4. First Action
- **Type:** Table
- **Purpose:** Guide operator to next triage action based on current state.
- **Data sources:** `bioetl_first_action`

### 5. Inputs
- **Type:** Table
- **Purpose:** Show input evidence for selected scope.
- **Data sources:** `bioetl_inputs`

### 6. Runtime
- **Type:** Table
- **Purpose:** Show runtime status and blockers.
- **Data sources:** `bioetl_runtime_status`, `bioetl_runtime_blockers`

### 7. Data Quality
- **Type:** Table
- **Purpose:** Show DQ status and validation results.
- **Data sources:** `bioetl_dq_status`, `bioetl_dq_validation_score`

### 8. Data Validation
- **Type:** Table
- **Purpose:** Show data validation outcomes.
- **Data sources:** `bioetl_data_validation_outcomes`

### 9. Control Plane
- **Type:** Table
- **Purpose:** Show control plane status and replay blockers.
- **Data sources:** `bioetl_control_plane_status`, `bioetl_replay_blockers`

### 10. Provider
- **Type:** Table
- **Purpose:** Show provider health and status.
- **Data sources:** `bioetl_provider_status`, `bioetl_provider_health`

### 11. Workflow
- **Type:** Table
- **Purpose:** Show workflow execution status.
- **Data sources:** `bioetl_workflow_status`, `bioetl_workflow_outcomes`

### 12. L1 Historical Trends
- **Type:** Row
- **Purpose:** Row-based historical trend workflow.
- **Data sources:** `bioetl_historical_trends`

### 13. Runtime Blockers Trend
- **Type:** Timeseries
- **Purpose:** Show runtime blockers trend over time.
- **Data sources:** `bioetl_runtime_blockers`

### 14. DQ Status Trend
- **Type:** Timeseries
- **Purpose:** Show DQ status trend over time.
- **Data sources:** `bioetl_dq_status`

### 15. Gold Lifecycle Trend
- **Type:** Timeseries
- **Purpose:** Show Gold lifecycle trend over time.
- **Data sources:** `bioetl_gold_lifecycle`

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
- **Purpose:** Row-based alert/SLO triage workflow.
- **Data sources:** `bioetl_alerts`, `bioetl_slo_pressure`

### 25. Triage Alert State
- **Type:** Table
- **Purpose:** Show alert state for triage.
- **Data sources:** `bioetl_alerts_active`, `bioetl_alerts_firing`

### 26. SLO/SLA Alert Pressure
- **Type:** Stat
- **Purpose:** Show SLO/SLA alert pressure indicators.
- **Data sources:** `bioetl_slo_alert_pressure`, `bioetl_sla_alert_pressure`

### 27. Firing Alert Details
- **Type:** Table
- **Purpose:** Show detailed information for currently firing alerts.
- **Data sources:** `bioetl_alerts_firing_total`, `bioetl_alerts_firing_by_alert_name`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows stage-specific evidence where the panel owns that selector.

## Notes

- This dashboard is the primary L1 entry point for incident triage.
- It uses shared shell/status/ID/provenance contracts across all primary dashboards.
- Row-based workflows (L1 Historical Trends, Range Evidence, Diagnostics & Docs, Alert/SLO Triage) provide structured triage paths.
- First Action panel provides operator guidance based on current state.
