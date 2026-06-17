# BioETL Workflow Overview - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-workflow-overview.json`

## Обзор

Dashboard `5. Workflow` monitors workflow and pipeline verdicts, failed runs,
step failures, skipped steps, and step duration trends. Shipped dashboard JSON
is the source of truth.

## Key Panels

### 1. Status
- **Type:** Stat
- **Purpose:** Summarize workflow run and step-event status.
- **Data sources:** `bioetl_workflow_runs_total`,
  `bioetl_workflow_step_events_total`

### 2. Pipeline Status
- **Type:** Stat
- **Purpose:** Compare runtime status with workflow pipeline verdict.
- **Data sources:** `bioetl_runtime_current_status`,
  `bioetl_workflow_pipeline_verdict_status`

### 3. Failed Runs and Steps
- **Type:** Stat
- **Purpose:** Count failed workflow runs, failed entity pipeline runs, failed
  pipeline steps, transform failures, and skipped events.
- **Data sources:** `bioetl_workflow_runs_total`,
  `bioetl_pipeline_runs_total`, `bioetl_workflow_step_events_total`

### 4. Workflow Outcomes and Step Trends
- **Type:** Bargauge / Timeseries
- **Purpose:** Inspect workflow outcomes, step outcomes, and step duration p95.
- **Data sources:** `bioetl_workflow_runs_total`,
  `bioetl_workflow_step_events_total`,
  `bioetl_workflow_step_duration_seconds_bucket`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary
  dashboard context shell.

## Notes

- Legacy workflow execution/status/rate placeholder metrics are intentionally
  not documented. Current panels use workflow run, pipeline run, runtime status,
  and workflow step metric families.
