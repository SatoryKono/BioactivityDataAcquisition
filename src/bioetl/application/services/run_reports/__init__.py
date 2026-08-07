"""Application services for writing pipeline/workflow run reports."""

from __future__ import annotations

from bioetl.application.services.run_reports.markdown import (
    render_pipeline_run_report_markdown,
    render_workflow_run_report_markdown,
)
from bioetl.application.services.run_reports.paths import (
    DEFAULT_REPORT_ROOT,
    resolve_report_root,
)
from bioetl.application.services.run_reports.query import (
    diff_pipeline_reports,
    list_pipeline_reports,
    list_workflow_reports,
    load_pipeline_report,
    load_workflow_report,
    prune_reports,
)
from bioetl.application.services.run_reports.writer import (
    RunReportWriteResult,
    write_pipeline_run_report,
    write_workflow_run_report,
)

__all__ = [
    "DEFAULT_REPORT_ROOT",
    "RunReportWriteResult",
    "diff_pipeline_reports",
    "list_pipeline_reports",
    "list_workflow_reports",
    "load_pipeline_report",
    "load_workflow_report",
    "prune_reports",
    "render_pipeline_run_report_markdown",
    "render_workflow_run_report_markdown",
    "resolve_report_root",
    "write_pipeline_run_report",
    "write_workflow_run_report",
]
