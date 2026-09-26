"""Declarative workflow runtime metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "WORKFLOW_CURRENT_STATUS",
    "WORKFLOW_EXPECTED",
    "WORKFLOW_PIPELINE_EXPECTED",
    "WORKFLOW_RECONCILIATION_ROWS_DELETED_TOTAL",
    "WORKFLOW_RECONCILIATION_ROWS_RETAINED_TOTAL",
    "WORKFLOW_RECONCILIATION_ROWS_SCANNED_TOTAL",
    "WORKFLOW_ROW_RECONCILIATION_EXCLUDED_ROWS_TOTAL",
    "WORKFLOW_ROW_RECONCILIATION_KEPT_ROWS_TOTAL",
    "WORKFLOW_ROW_RECONCILIATION_LEFT_ROWS_TOTAL",
    "WORKFLOW_ROW_RECONCILIATION_RIGHT_ROWS_TOTAL",
    "WORKFLOW_RUNS_TOTAL",
    "WORKFLOW_STEP_DURATION_SECONDS",
    "WORKFLOW_STEP_EVENTS_TOTAL",
]

WORKFLOW_RUNS_TOTAL = Counter(
    "bioetl_workflow_runs_total",
    "Total declarative workflow run outcomes by bounded workflow and status",
    ["workflow", "status", "pipeline_context", "run_type_context", "provider_context"],
)

WORKFLOW_CURRENT_STATUS = Gauge(
    "bioetl_workflow_current_status",
    "Current terminal workflow status by bounded workflow context: 0=OK, 1=WARN, 2=CRIT",
    ["workflow", "pipeline_context", "run_type_context", "provider_context"],
)

WORKFLOW_EXPECTED = Gauge(
    "bioetl_workflow_expected",
    "Planned workflow scopes for dashboard selector universes",
    ["workflow", "provider"],
)

WORKFLOW_PIPELINE_EXPECTED = Gauge(
    "bioetl_workflow_pipeline_expected",
    "Planned workflow pipeline/run_type scopes for dashboard selector universes",
    ["workflow", "pipeline", "run_type", "provider"],
)

WORKFLOW_RECONCILIATION_ROWS_SCANNED_TOTAL = Counter(
    "bioetl_workflow_reconciliation_rows_scanned_total",
    "Total workflow reconciliation rows scanned",
)

WORKFLOW_RECONCILIATION_ROWS_RETAINED_TOTAL = Counter(
    "bioetl_workflow_reconciliation_rows_retained_total",
    "Total workflow reconciliation rows retained",
)

WORKFLOW_RECONCILIATION_ROWS_DELETED_TOTAL = Counter(
    "bioetl_workflow_reconciliation_rows_deleted_total",
    "Total workflow reconciliation rows deleted",
)

WORKFLOW_ROW_RECONCILIATION_LEFT_ROWS_TOTAL = Counter(
    "bioetl_workflow_row_reconciliation_left_rows_total",
    "Total left-side rows inspected by workflow row reconciliation",
    ["layer"],
)

WORKFLOW_ROW_RECONCILIATION_RIGHT_ROWS_TOTAL = Counter(
    "bioetl_workflow_row_reconciliation_right_rows_total",
    "Total right-side rows inspected by workflow row reconciliation",
    ["layer"],
)

WORKFLOW_ROW_RECONCILIATION_KEPT_ROWS_TOTAL = Counter(
    "bioetl_workflow_row_reconciliation_kept_rows_total",
    "Total rows retained by workflow row reconciliation",
    ["layer"],
)

WORKFLOW_ROW_RECONCILIATION_EXCLUDED_ROWS_TOTAL = Counter(
    "bioetl_workflow_row_reconciliation_excluded_rows_total",
    "Total rows excluded by workflow row reconciliation",
    ["layer"],
)

WORKFLOW_STEP_EVENTS_TOTAL = Counter(
    "bioetl_workflow_step_events_total",
    "Total declarative workflow step outcomes by bounded workflow, step kind, and status",
    [
        "workflow",
        "step_kind",
        "status",
        "pipeline_context",
        "run_type_context",
        "provider_context",
    ],
)

WORKFLOW_STEP_DURATION_SECONDS = Histogram(
    "bioetl_workflow_step_duration_seconds",
    "Duration of declarative workflow step execution by bounded workflow, step kind, and status",
    [
        "workflow",
        "step_kind",
        "status",
        "pipeline_context",
        "run_type_context",
        "provider_context",
    ],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)
