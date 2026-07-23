"""Application services for writing pipeline/workflow run reports."""

from __future__ import annotations

from bioetl.application.services.run_reports.markdown import (
    render_pipeline_run_report_markdown,
    render_workflow_run_report_markdown,
)
from bioetl.application.services.run_reports.writer import (
    RunReportWriteResult,
    write_pipeline_run_report,
    write_workflow_run_report,
)

__all__ = [
    "RunReportWriteResult",
    "render_pipeline_run_report_markdown",
    "render_workflow_run_report_markdown",
    "write_pipeline_run_report",
    "write_workflow_run_report",
]
