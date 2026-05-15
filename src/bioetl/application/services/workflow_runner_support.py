"""Internal state and helper functions for workflow runner orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.application.services.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformExecutionResult,
)
from bioetl.application.services.workflow_transition_policy import (
    WorkflowStepDefinition,
    WorkflowStepTransitionPolicy,
    step_kind_for_config,
)
from bioetl.domain.workflow import WorkflowRunOptionsConfig

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bioetl.domain.ports import MetricsPort

_WORKFLOW_RUNS_TOTAL = "bioetl_workflow_runs_total"
_WORKFLOW_CURRENT_STATUS = "bioetl_workflow_current_status"
_WORKFLOW_STEP_EVENTS_TOTAL = "bioetl_workflow_step_events_total"
_WORKFLOW_STEP_DURATION_SECONDS = "bioetl_workflow_step_duration_seconds"


@dataclass(slots=True)
class WorkflowExecutionState:
    """Mutable state for one in-process workflow execution."""

    step_results: list[WorkflowStepExecutionResult]
    step_outputs: dict[str, object]
    status: str = "success"
    failed_step_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedWorkflowStepTransition:
    """Execution result paired with the pure transition policy."""

    policy: WorkflowStepTransitionPolicy
    result: WorkflowStepExecutionResult


def record_workflow_run_metrics(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    status: str,
    context_labels: Mapping[str, str],
) -> None:
    """Record terminal workflow status metrics."""
    metrics.set_gauge(
        _WORKFLOW_CURRENT_STATUS,
        workflow_status_to_gauge_value(status),
        {
            "workflow": workflow_name,
            **context_labels,
        },
    )
    metrics.increment_counter(
        _WORKFLOW_RUNS_TOTAL,
        1,
        {
            "workflow": workflow_name,
            "status": status,
            **context_labels,
        },
    )


def build_skipped_step_result(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step: WorkflowStepDefinition,
    failed_step_id: str,
    context_labels: Mapping[str, str],
) -> WorkflowStepExecutionResult:
    """Build the canonical downstream-skip result after an upstream failure."""
    step_kind = step_kind_for_config(step)
    record_step_metrics(
        metrics=metrics,
        workflow_name=workflow_name,
        step_kind=step_kind,
        status="skipped",
        duration_seconds=0.0,
        context_labels=context_labels,
    )
    return WorkflowStepExecutionResult(
        step_id=step.step_id,
        step_kind=step_kind,
        status="skipped",
        error_type="UpstreamStepFailed",
        error_message=(
            f"Skipped because upstream step '{failed_step_id}' failed before "
            "this step could execute."
        ),
    )


def build_resume_skipped_step_result(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step: WorkflowStepDefinition,
    context_labels: Mapping[str, str],
) -> WorkflowStepExecutionResult:
    """Build the canonical resume-skip result for already completed steps."""
    step_kind = step_kind_for_config(step)
    record_step_metrics(
        metrics=metrics,
        workflow_name=workflow_name,
        step_kind=step_kind,
        status="skipped",
        duration_seconds=0.0,
        context_labels=context_labels,
    )
    return WorkflowStepExecutionResult(
        step_id=step.step_id,
        step_kind=step_kind,
        status="skipped",
        error_type="AlreadyCompletedOnResume",
        error_message=(
            "Skipped because this step completed successfully in the last "
            "persisted workflow execution state."
        ),
    )


def record_step_metrics(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step_kind: str,
    status: str,
    duration_seconds: float,
    context_labels: Mapping[str, str],
) -> None:
    """Record step event counters and duration histogram consistently."""
    metrics.increment_counter(
        _WORKFLOW_STEP_EVENTS_TOTAL,
        1,
        {
            "workflow": workflow_name,
            "step_kind": step_kind,
            "status": status,
            **context_labels,
        },
    )
    metrics.observe_histogram(
        _WORKFLOW_STEP_DURATION_SECONDS,
        max(duration_seconds, 0.0),
        {
            "workflow": workflow_name,
            "step_kind": step_kind,
            "status": status,
            **context_labels,
        },
    )


def step_result_from_transform_result(
    result: WorkflowTransformExecutionResult,
) -> WorkflowStepExecutionResult:
    """Normalize transform execution into the shared step result envelope."""
    return WorkflowStepExecutionResult(
        step_id=result.step_id,
        step_kind="transform",
        status=result.status,
        payload=result,
        error_type=result.error_type,
        error_message=result.error_message,
    )


def run_options_from_config(config: WorkflowRunOptionsConfig) -> RunOptions:
    """Project workflow run options onto pipeline runner options."""
    return RunOptions(**config.to_mapping())


def workflow_result_from_state(
    workflow_name: str,
    state: WorkflowExecutionState,
) -> WorkflowRunExecutionResult:
    """Project mutable workflow state onto the stable public result."""
    failed_step = next(
        (step for step in state.step_results if step.status == "failed"),
        None,
    )
    return WorkflowRunExecutionResult(
        workflow_name=workflow_name,
        status=state.status,
        steps=tuple(state.step_results),
        error_type=None if failed_step is None else failed_step.error_type,
        error_message=None if failed_step is None else failed_step.error_message,
    )


def workflow_status_to_gauge_value(status: str) -> float:
    """Map terminal workflow states onto the canonical L0 severity enum."""
    if status in {"success", "completed"}:
        return 0.0
    if status == "failed":
        return 2.0
    return 1.0


__all__ = [
    "ResolvedWorkflowStepTransition",
    "WorkflowExecutionState",
    "build_resume_skipped_step_result",
    "build_skipped_step_result",
    "record_step_metrics",
    "record_workflow_run_metrics",
    "run_options_from_config",
    "step_result_from_transform_result",
    "workflow_result_from_state",
    "workflow_status_to_gauge_value",
]
