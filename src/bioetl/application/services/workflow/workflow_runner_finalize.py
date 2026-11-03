"""Finalize helpers for WorkflowRunnerService run completion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
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

__all__ = ["finalize_workflow_run_result"]


def _require_workflow_result(value: object) -> WorkflowRunExecutionResult:
    """Return a concrete workflow result after validating replacement output."""
    if not isinstance(value, WorkflowRunExecutionResult):
        raise TypeError(
            "dataclass replacement did not preserve WorkflowRunExecutionResult"
        )
    return value


def finalize_workflow_run_result(
    *,
    config: WorkflowConfig,
    state: WorkflowExecutionState,
    workflow_context_labels: Mapping[str, str],
    workflow_run_id: str | None,
    manifest_id: str | None,
    execution_fingerprint: str | None,
    resumed: bool,
    started_at: datetime,
    started_monotonic: float,
    metrics: MetricsPort,
    report_store: RunReportStorePort,
    report_root: Path | None,
    logger: LoggerPort | None,
    archive_control_plane: Callable[..., None] | None,
    evidence_location_verify: Callable[[WorkflowRunExecutionResult], None] | None,
) -> WorkflowRunExecutionResult:
    """Record metrics, attach the run report, and archive child evidence."""
    record_workflow_run_metrics(
        metrics=metrics,
        workflow_name=config.name,
        status=state.status,
        context_labels=workflow_context_labels,
    )
    result = workflow_result_from_state(config.name, state)
    identified_result = _require_workflow_result(
        replace(
            result,
            workflow_run_id=workflow_run_id,
            manifest_id=manifest_id,
            execution_fingerprint=execution_fingerprint,
            resumed=resumed,
            started_at=started_at.isoformat(),
            completed_at=current_utc_time().isoformat(),
            duration_seconds=perf_counter() - started_monotonic,
        )
    )
    # RF-004: reuse outer prepare→report scope when present; else bind locally.
    observation_token = bind_run_observations_if_unbound()
    try:
        if evidence_location_verify is not None:
            try:
                evidence_location_verify(identified_result)
            except Exception as exc:
                # Consistency diagnostics must not mask processing success.
                record_verify_exception_observation(
                    kind="workflow",
                    owner=str(identified_result.workflow_name),
                    run_id=str(identified_result.workflow_run_id or ""),
                    exc=exc,
                )
        reported = attach_workflow_run_report(
            config=config,
            result=identified_result,
            logger=logger,
            store=report_store,
            report_root=report_root,
        )
        archive_workflow_children(config, reported, archive_control_plane)
        return reported
    finally:
        reset_run_observations_if_bound(observation_token)
