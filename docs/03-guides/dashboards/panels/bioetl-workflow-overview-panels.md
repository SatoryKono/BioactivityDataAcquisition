# BioETL Workflow Overview - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-workflow-overview.json`

## Обзор

Dashboard `5. Workflow` monitors workflow and pipeline verdicts, failed runs,
step failures, skipped steps, and step duration trends. Shipped dashboard JSON
is the source of truth.

## Variable contract

- All panels inherit the shared shell selectors: `workflow`, `pipeline`,
  `run_type`, `run_id`.
- Workflow-specific drilldown selectors add `status`, `workflow_context`,
  `pipeline_context`, `pipeline_context_exact`, `run_type_context`,
  `run_type_context_exact`, `provider_context`, `provider_context_exact`,
  `step_status`, and `step_kind`.
- `ID` and `Processed Records` use the detached `Quarantine Explorer`
  datasource; the rest of the dashboard is Prometheus-backed.

## Panel inventory

### Dashboard shell

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 1000 | Review Dashboard Navigation | text | Static | Static navigation handoff into related runtime, provider, and pipeline dashboards. | shared shell | No thresholds; operator routing only. |
| 9400 | Provenance | text | Static | Static explanation of selector context, datasource posture, and workflow evidence boundaries. | shared shell | No thresholds; provenance note only. |
| 9401 | Status | stat | Prometheus | Current workflow severity synthesized from failed workflow runs and skipped step events in the selected range. | shared shell | Value mapping expresses current workflow severity. |
| 9404 | Pipeline Status | stat | Prometheus | Workflow pipeline verdict status with fallback to runtime current status. | shared shell + context selectors | Value mapping expresses current pipeline severity. |
| 9402 | ID | table | Quarantine Explorer | Identity anchors for the selected workflow/pipeline/run scope. | shared shell | Forensic handoff table. |
| 9403 | Processed Records | table | Quarantine Explorer | Processed-record evidence for the selected workflow/pipeline/run scope. | shared shell | Evidence table; no numeric threshold. |
| 2 | Failed Workflow Runs / Range | stat | Prometheus | Failed workflow-run count over the selected range. | shared shell | Count panel. |
| 3 | Failed Pipeline Steps / Range | stat | Prometheus | Failed workflow step events with `step_kind="pipeline"`. | shared shell | Count panel. |
| 9410 | Failed Entity Pipeline Runs / Range | stat | Prometheus | Failed entity pipeline runs over the selected range. | shared shell + context selectors | Count panel. |
| 6 | Failed Transform Steps / Range | stat | Prometheus | Failed workflow step events with `step_kind="transform"`. | shared shell | Count panel. |
| 7 | Skipped Step Events / Range | stat | Prometheus | Skipped workflow step events over the selected range. | shared shell | Count panel. |
| 4 | Workflow Run Outcomes / Range | stat | Prometheus | Compact selected-range total for workflow run outcomes across the active status filter. | shared shell + `status` | `0` maps to neutral `NO OUTCOME EVENTS`; failed/skipped severity stays in the dedicated cards. |
| 9 | First Action | text | Static | Static triage guidance for the first workflow drilldown action. | shared shell | No thresholds; operator routing only. |

### Step Diagnostics

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | Step Diagnostics | row | Static | Collapsible workflow step-diagnostics section. | shared shell + step/context selectors | Groups step drilldown panels; no direct metric. |
| 5 | Step Outcomes by Kind / Step Status / Range | timeseries | Prometheus | Workflow step-event outcomes by `step_kind` and `status`. | shared shell + `step_kind` + `step_status` | Series legend is the key mapping. |
| 8 | Step Duration p95 by Kind / Step Status / Range | timeseries | Prometheus | Histogram-quantile `p95` workflow step duration by `step_kind` and `status`. | shared shell + `step_kind` + `step_status` | Quantile family and legend are the key mapping. |

## PromQL Formula Anchors

The shipped dashboard JSON remains the byte-level source of truth. The formulas
below document the current Prometheus query families so this page is auditable
without opening Grafana JSON for every panel.

- `Status`:
  `max(((round(sum(increase(bioetl_workflow_runs_total{workflow=~"$workflow",status="failed"}[$__range]))) > bool 0) * 2) or ((round(sum(increase(bioetl_workflow_step_events_total{workflow=~"$workflow",status="skipped"}[$__range]))) > bool 0) * 1) or ((round(sum(increase(bioetl_workflow_runs_total{workflow=~"$workflow",status!~"success|failed"}[$__range]))) > bool 0) * 1))`
- `Pipeline Status`:
  `max(bioetl_workflow_pipeline_verdict_status{pipeline=~"$pipeline_context",run_type=~"$run_type_context"}) or max(bioetl_runtime_current_status{pipeline=~"$pipeline",run_type=~"$run_type"})`
- `Failed Workflow Runs / Range`:
  `round(sum(increase(bioetl_workflow_runs_total{workflow=~"$workflow",status="failed"}[$__range]))) or vector(0)`
- `Failed Pipeline Steps / Range`:
  `round(sum(increase(bioetl_workflow_step_events_total{workflow=~"$workflow",step_kind="pipeline",status="failed"}[$__range]))) or vector(0)`
- `Failed Entity Pipeline Runs / Range`:
  `round(sum(increase(bioetl_pipeline_runs_total{pipeline=~"$pipeline_context",run_type=~"$run_type_context",status="failed"}[$__range]))) or vector(0)`
- `Failed Transform Steps / Range`:
  `round(sum(increase(bioetl_workflow_step_events_total{workflow=~"$workflow",step_kind="transform",status="failed"}[$__range]))) or vector(0)`
- `Skipped Step Events / Range`:
  `round(sum(increase(bioetl_workflow_step_events_total{workflow=~"$workflow",status="skipped"}[$__range]))) or vector(0)`
- `Workflow Run Outcomes / Range`:
  `round(sum(increase(bioetl_workflow_runs_total{workflow=~"$workflow",status=~"$status"}[$__range]))) or vector(0)`
- `Step Outcomes by Kind / Step Status / Range`:
  `sum by (step_kind, status) (increase(bioetl_workflow_step_events_total{workflow=~"$workflow",step_kind=~"$step_kind",status=~"$step_status"}[$__range]))`
- `Step Duration p95 by Kind / Step Status / Range`:
  `histogram_quantile(0.95, sum by (le, step_kind, status) (max_over_time(bioetl_workflow_step_duration_seconds_bucket{workflow=~"$workflow",step_kind=~"$step_kind",status=~"$step_status"}[$__range])))`

## Notes

- `Pipeline Status` intentionally merges workflow verdict status with runtime
  current status so workflow-only gaps still surface a pipeline state.
- `Workflow Run Outcomes / Range` intentionally uses a neutral compact `stat`
  instead of a status-colored bar gauge so an empty selected range does not
  render as large `success=0` / `failed=0` bars.
- `ID` and `Processed Records` are HTTP-backed evidence panels rather than
  Prometheus metric panels.
- Thresholds and value mappings not spelled out above should be taken from the
  shipped panel JSON; this page documents the panel inventory, datasource
  family, primary PromQL formulas, and operator purpose 1:1.
