# BioETL Overview v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

## Обзор

Dashboard `1. Overview` is the L0 operator entry surface. It answers current
system status, first action, and drilldown routing across Runtime, DQ, Gold,
Control Plane, Provider, and Workflow dashboards.

## Key Panels

### 1. Status
- **Type:** Stat
- **Purpose:** Current L0 severity for the selected scope.
- **Data sources:** `bioetl_l0_status`

### 2. First Action
- **Type:** Table
- **Purpose:** Route the operator to the highest-priority next dashboard.
- **Data sources:** `bioetl_l0_next_action_route`,
  `bioetl_overview_pipeline_run_type_universe`

### 3. Inputs
- **Type:** Table
- **Purpose:** Show per-domain L0 input status.
- **Data sources:** `bioetl_l0_input_status_selected`

### 4. Domain Scorecards
- **Type:** Table / Timeseries
- **Purpose:** Expose current and historical status for Runtime, DQ, Gold,
  Control Plane, Provider, and Workflow.
- **Data sources:** `bioetl_l1_runtime_blocker_status`,
  `bioetl_l1_dq_status`, `bioetl_l1_gold_lifecycle_status`,
  `bioetl_l1_control_plane_current_status`,
  `bioetl_l1_provider_global_status`, `bioetl_l1_workflow_global_status`

### 5. Historical Runs and Silver Reject Summary
- **Type:** Table / Stat
- **Purpose:** Show recent terminal pipeline runs and selected-range Silver
  reject summary.
- **Data sources:** `bioetl_pipeline_runs_total`,
  `bioetl_records_processed_total`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary
  dashboard context shell.
- Overview defaults to `Workflow=All`, `Pipeline=All`, `Run Type=All`, and
  `Run ID=-`.

## Notes

- Overview does not own provider latency, generic DQ score, quarantine-rate, or
  legacy singular pipeline-run metrics. Those stale names were removed from this
  mirror so the dashboarded/declaration inventory reflects the shipped JSON.
