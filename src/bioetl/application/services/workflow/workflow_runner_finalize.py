"""Finalize helpers for WorkflowRunnerService run completion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.control_plane.evidence_location import (
    record_verify_exception_observation,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations_if_unbound,
    reset_run_observations_if_bound,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    archive_workflow_children,
    attach_workflow_run_report,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    WorkflowExecutionState,
    record_workflow_run_metrics,
    workflow_result_from_state,
)
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.workflow import WorkflowConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = [
    "WorkflowFinalizeContext",
    "finalize_workflow_run_result",
]


@dataclass(frozen=True, slots=True)
class WorkflowFinalizeContext:
    """Packed finalize inputs (python:S107)."""

    config: WorkflowConfig
    state: WorkflowExecutionState
    workflow_context_labels: Mapping[str, str]
    workflow_run_id: str | None
    manifest_id: str | None
    execution_fingerprint: str | None
    resumed: bool
    started_at: datetime
    started_monotonic: float
    metrics: MetricsPort
    report_store: RunReportStorePort
    report_root: Path | None
    logger: LoggerPort | None
    archive_control_plane: Callable[..., None] | None
    evidence_location_verify: Callable[[WorkflowRunExecutionResult], None] | None


def _require_workflow_result(value: object) -> WorkflowRunExecutionResult:
    """Return a concrete workflow result after validating replacement output."""
    if not isinstance(value, WorkflowRunExecutionResult):
        raise TypeError(
            "dataclass replacement did not preserve WorkflowRunExecutionResult"
        )
    return value


def finalize_workflow_run_result(
    context: WorkflowFinalizeContext,
) -> WorkflowRunExecutionResult:
    """Record metrics, attach the run report, and archive child evidence."""
    record_workflow_run_metrics(
        metrics=context.metrics,
        workflow_name=context.config.name,
        status=context.state.status,
        context_labels=context.workflow_context_labels,
    )
    result = workflow_result_from_state(context.config.name, context.state)
    identified_result = _require_workflow_result(
        replace(
            result,
            workflow_run_id=context.workflow_run_id,
            manifest_id=context.manifest_id,
            execution_fingerprint=context.execution_fingerprint,
            resumed=context.resumed,
            started_at=context.started_at.isoformat(),
            completed_at=current_utc_time().isoformat(),
            duration_seconds=perf_counter() - context.started_monotonic,
        )
    )
    # RF-004: reuse outer prepare→report scope when present; else bind locally.
    observation_token = bind_run_observations_if_unbound()
    try:
        if context.evidence_location_verify is not None:
            try:
                context.evidence_location_verify(identified_result)
            except Exception as exc:
                # Consistency diagnostics must not mask processing success.
                record_verify_exception_observation(
                    kind="workflow",
                    owner=str(identified_result.workflow_name),
                    run_id=str(identified_result.workflow_run_id or ""),
                    exc=exc,
                )
        reported = attach_workflow_run_report(
            config=context.config,
            result=identified_result,
            logger=context.logger,
            store=context.report_store,
            report_root=context.report_root,
        )
        archive_workflow_children(
            context.config, reported, context.archive_control_plane
        )
        return reported
    finally:
        reset_run_observations_if_bound(observation_token)
