"""Workflow runner service for declarative pipeline and transform DAGs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformDestructiveCommit,
    WorkflowTransformExecutionResult,
    WorkflowTransformService,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
    WorkflowTransformSpec,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "WorkflowRunExecutionResult",
    "WorkflowRunnerService",
    "WorkflowStepExecutionResult",
]

_WORKFLOW_RUNS_TOTAL = "bioetl_workflow_runs_total"
_WORKFLOW_CURRENT_STATUS = "bioetl_workflow_current_status"
_WORKFLOW_STEP_EVENTS_TOTAL = "bioetl_workflow_step_events_total"
_WORKFLOW_STEP_DURATION_SECONDS = "bioetl_workflow_step_duration_seconds"
_STEP_KIND_PIPELINE = "pipeline"
_WORKFLOW_STEP_FAILURES = (
    BioETLError,
    KeyError,
    RuntimeError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True, slots=True)
class WorkflowStepExecutionResult:
    """Normalized result for one workflow DAG step."""

    step_id: str
    step_kind: str
    status: str
    payload: object | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowRunExecutionResult:
    """Normalized result for one declarative workflow run."""

    workflow_name: str
    status: str
    steps: tuple[WorkflowStepExecutionResult, ...]
    workflow_run_id: str | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Return whether every workflow step completed or was skipped."""
        return self.status == "success"


@dataclass(slots=True)
class _WorkflowExecutionState:
    """Mutable state for one in-process workflow execution."""

    step_results: list[WorkflowStepExecutionResult]
    step_outputs: dict[str, object]
    status: str = "success"
    failed_step_id: str | None = None


@dataclass(frozen=True, slots=True)
class _WorkflowStepTransition:
    """Result of resolving one workflow step transition."""

    result: WorkflowStepExecutionResult
    stores_output: bool


@dataclass(slots=True)
class WorkflowRunnerService:
    """Execute workflow pipeline and transform steps in topological order."""

    pipeline_runner: PipelineRunnerService
    transform_service: WorkflowTransformService
    metrics: MetricsPort
    monotonic: Callable[[], float] = perf_counter

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        completed_step_ids: frozenset[str] | None = None,
        completed_transform_fingerprints: dict[str, str] | None = None,
        step_started_callback: Callable[..., None] | None = None,
        step_completed_callback: Callable[[WorkflowStepExecutionResult], None]
        | None = None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ) = None,
    ) -> WorkflowRunExecutionResult:
        """Run a workflow config and stop on first failed step."""
        state = _WorkflowExecutionState(step_results=[], step_outputs={})
        workflow_context_labels = config.workflow_context_labels

        for step_id in config.topological_step_ids:
            step = config.get_step(step_id)
            if step is None:
                continue
            transition = await self._resolve_step_transition(
                workflow_name=config.name,
                step=step,
                state=state,
                workflow_context_labels=workflow_context_labels,
                completed_step_ids=completed_step_ids,
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=step_started_callback,
                transform_commit_callback=transform_commit_callback,
            )
            self._apply_step_transition(
                state=state,
                step=step,
                transition=transition,
                step_completed_callback=step_completed_callback,
            )

        _record_workflow_run_metrics(
            metrics=self.metrics,
            workflow_name=config.name,
            status=state.status,
            context_labels=workflow_context_labels,
        )
        return _workflow_result_from_state(config.name, state)

    async def _resolve_step_transition(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig | TransformStepConfig,
        state: _WorkflowExecutionState,
        workflow_context_labels: Mapping[str, str],
        completed_step_ids: frozenset[str] | None,
        completed_transform_fingerprints: dict[str, str] | None,
        step_started_callback: Callable[..., None] | None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ),
    ) -> _WorkflowStepTransition:
        """Resolve whether a step should run, resume-skip, or failure-skip."""
        if state.failed_step_id is not None:
            return _WorkflowStepTransition(
                result=_build_skipped_step_result(
                    metrics=self.metrics,
                    workflow_name=workflow_name,
                    step=step,
                    failed_step_id=state.failed_step_id,
                    context_labels=workflow_context_labels,
                ),
                stores_output=False,
            )
        if completed_step_ids and step.step_id in completed_step_ids:
            return _WorkflowStepTransition(
                result=_build_resume_skipped_step_result(
                    metrics=self.metrics,
                    workflow_name=workflow_name,
                    step=step,
                    context_labels=workflow_context_labels,
                ),
                stores_output=False,
            )
        return _WorkflowStepTransition(
            result=await self._run_step(
                workflow_name=workflow_name,
                step=step,
                step_outputs=state.step_outputs,
                workflow_context_labels=workflow_context_labels,
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=step_started_callback,
                transform_commit_callback=transform_commit_callback,
            ),
            stores_output=True,
        )

    def _apply_step_transition(
        self,
        *,
        state: _WorkflowExecutionState,
        step: WorkflowStepConfig | TransformStepConfig,
        transition: _WorkflowStepTransition,
        step_completed_callback: Callable[[WorkflowStepExecutionResult], None] | None,
    ) -> None:
        """Apply one resolved transition to mutable workflow execution state."""
        result = transition.result
        state.step_results.append(result)
        if step_completed_callback is not None:
            step_completed_callback(result)
        if transition.stores_output:
            state.step_outputs[step.step_id] = result.payload
        if result.status == "failed":
            state.status = "failed"
            state.failed_step_id = step.step_id

    async def _run_step(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig | TransformStepConfig,
        step_outputs: dict[str, object],
        workflow_context_labels: Mapping[str, str],
        completed_transform_fingerprints: dict[str, str] | None,
        step_started_callback: Callable[..., None] | None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ),
    ) -> WorkflowStepExecutionResult:
        if isinstance(step, WorkflowStepConfig):
            return await self._run_pipeline_step(
                workflow_name=workflow_name,
                step=step,
                workflow_context_labels=workflow_context_labels,
                step_started_callback=step_started_callback,
            )
        return await self._run_transform_step(
            workflow_name=workflow_name,
            step=step,
            step_outputs=step_outputs,
            workflow_context_labels=workflow_context_labels,
            completed_transform_fingerprints=completed_transform_fingerprints,
            step_started_callback=step_started_callback,
            transform_commit_callback=transform_commit_callback,
        )

    async def _run_pipeline_step(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig,
        workflow_context_labels: Mapping[str, str],
        step_started_callback: Callable[..., None] | None,
    ) -> WorkflowStepExecutionResult:
        if step_started_callback is not None:
            step_started_callback(step, fingerprint=None)
        started = self.monotonic()
        try:
            result = await self.pipeline_runner.run(
                step.pipeline_name,
                options=_run_options_from_config(step.run_options),
            )
        except _WORKFLOW_STEP_FAILURES as exc:
            _record_step_metrics(
                metrics=self.metrics,
                workflow_name=workflow_name,
                step_kind=_STEP_KIND_PIPELINE,
                status="failed",
                duration_seconds=self.monotonic() - started,
                context_labels=workflow_context_labels,
            )
            return WorkflowStepExecutionResult(
                step_id=step.step_id,
                step_kind=_STEP_KIND_PIPELINE,
                status="failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        status = "success" if result.is_success else "failed"
        _record_step_metrics(
            metrics=self.metrics,
            workflow_name=workflow_name,
            step_kind=_STEP_KIND_PIPELINE,
            status=status,
            duration_seconds=self.monotonic() - started,
            context_labels=workflow_context_labels,
        )
        return WorkflowStepExecutionResult(
            step_id=step.step_id,
            step_kind=_STEP_KIND_PIPELINE,
            status=status,
            payload=result,
            error_type=getattr(result, "error_type", None),
            error_message=getattr(result, "error_message", None),
        )

    async def _run_transform_step(
        self,
        *,
        workflow_name: str,
        step: TransformStepConfig,
        step_outputs: dict[str, object],
        workflow_context_labels: Mapping[str, str],
        completed_transform_fingerprints: dict[str, str] | None,
        step_started_callback: Callable[..., None] | None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ),
    ) -> WorkflowStepExecutionResult:
        spec = WorkflowTransformSpec.from_step(step)
        if step_started_callback is not None:
            step_started_callback(step, fingerprint=spec.fingerprint)
        upstream_outputs = {
            dependency: step_outputs[dependency]
            for dependency in step.depends_on
            if dependency in step_outputs
        }
        result = await self.transform_service.run_step(
            workflow_name=workflow_name,
            step=step,
            upstream_outputs=upstream_outputs,
            context_labels=workflow_context_labels,
            completed_fingerprints=completed_transform_fingerprints,
            destructive_commit_callback=transform_commit_callback,
        )
        return _step_result_from_transform_result(result)


def _record_workflow_run_metrics(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    status: str,
    context_labels: Mapping[str, str],
) -> None:
    """Record terminal workflow status metrics."""
    metrics.set_gauge(
        _WORKFLOW_CURRENT_STATUS,
        _workflow_status_to_gauge_value(status),
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


def _build_skipped_step_result(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step: WorkflowStepConfig | TransformStepConfig,
    failed_step_id: str,
    context_labels: Mapping[str, str],
) -> WorkflowStepExecutionResult:
    step_kind = _step_kind_for_config(step)
    _record_step_metrics(
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


def _build_resume_skipped_step_result(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step: WorkflowStepConfig | TransformStepConfig,
    context_labels: Mapping[str, str],
) -> WorkflowStepExecutionResult:
    step_kind = _step_kind_for_config(step)
    _record_step_metrics(
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


def _step_kind_for_config(step: WorkflowStepConfig | TransformStepConfig) -> str:
    return _STEP_KIND_PIPELINE if isinstance(step, WorkflowStepConfig) else "transform"


def _record_step_metrics(
    *,
    metrics: MetricsPort,
    workflow_name: str,
    step_kind: str,
    status: str,
    duration_seconds: float,
    context_labels: Mapping[str, str],
) -> None:
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


def _step_result_from_transform_result(
    result: WorkflowTransformExecutionResult,
) -> WorkflowStepExecutionResult:
    return WorkflowStepExecutionResult(
        step_id=result.step_id,
        step_kind="transform",
        status=result.status,
        payload=result,
        error_type=result.error_type,
        error_message=result.error_message,
    )


def _run_options_from_config(config: WorkflowRunOptionsConfig) -> RunOptions:
    return RunOptions(**config.to_mapping())


def _workflow_result_from_state(
    workflow_name: str,
    state: _WorkflowExecutionState,
) -> WorkflowRunExecutionResult:
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


def _workflow_status_to_gauge_value(status: str) -> float:
    """Map terminal workflow states onto the canonical L0 severity enum."""
    if status in {"success", "completed"}:
        return 0.0
    if status == "failed":
        return 2.0
    return 1.0
