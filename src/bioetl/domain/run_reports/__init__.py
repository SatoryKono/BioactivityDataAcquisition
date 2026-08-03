"""Domain models and builders for pipeline/workflow run reports."""

from __future__ import annotations

from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.context import (
    bind_stage_accounting,
    get_stage_accounting,
    reset_stage_accounting,
)
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    LayerCounts,
    PipelineRunReport,
    ReasonRemoval,
    StageFunnelRow,
    TrackingCoverage,
    WorkflowExecutionRow,
    WorkflowRunReport,
)
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.domain.run_reports.reason_catalog import (
    REASON_CATALOG_VERSION,
    ReasonCatalog,
    default_reason_catalog,
    normalize_reason_code,
)
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report

__all__ = [
    "REASON_CATALOG_VERSION",
    "BalanceStatus",
    "LayerCounts",
    "PipelineRunReport",
    "ReasonCatalog",
    "ReasonRemoval",
    "StageAccountingAccumulator",
    "StageFunnelRow",
    "TrackingCoverage",
    "WorkflowExecutionRow",
    "WorkflowRunReport",
    "bind_stage_accounting",
    "build_pipeline_run_report",
    "build_workflow_run_report",
    "default_reason_catalog",
    "get_stage_accounting",
    "normalize_reason_code",
    "reset_stage_accounting",
]
