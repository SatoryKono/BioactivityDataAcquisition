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
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Return whether every workflow step completed or was skipped."""
        return self.status == "success"


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
        step_results: list[WorkflowStepExecutionResult] = []
        step_outputs: dict[str, object] = {}
        status = "success"
        failed_step_id: str | None = None
        workflow_context_labels = config.workflow_context_labels

        for step_id in config.topological_step_ids:
            step = config.get_step(step_id)
            if step is None:
                continue
            if failed_step_id is not None:
                skipped = self._build_skipped_step_result(
                    workflow_name=config.name,
                    step=step,
                    failed_step_id=failed_step_id,
                    context_labels=workflow_context_labels,
                )
                step_results.append(skipped)
                if step_completed_callback is not None:
                    step_completed_callback(skipped)
                continue
            if completed_step_ids and step.step_id in completed_step_ids:
                skipped = self._build_resume_skipped_step_result(
                    workflow_name=config.name,
                    step=step,
                    context_labels=workflow_context_labels,
                )
                step_results.append(skipped)
                if step_completed_callback is not None:
                    step_completed_callback(skipped)
                continue
            result = await self._run_step(
                workflow_name=config.name,
                step=step,
                step_outputs=step_outputs,
                workflow_context_labels=workflow_context_labels,
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=step_started_callback,
                transform_commit_callback=transform_commit_callback,
            )
            step_results.append(result)
            if step_completed_callback is not None:
                step_completed_callback(result)
            step_outputs[step.step_id] = result.payload
            if result.status == "failed":
                status = "failed"
                failed_step_id = step.step_id

        self.metrics.set_gauge(
            _WORKFLOW_CURRENT_STATUS,
            _workflow_status_to_gauge_value(status),
            {
                "workflow": config.name,
                **workflow_context_labels,
            },
        )
        self.metrics.increment_counter(
            _WORKFLOW_RUNS_TOTAL,
            1,
            {
                "workflow": config.name,
                "status": status,
                **workflow_context_labels,
            },
        )
        return WorkflowRunExecutionResult(
            workflow_name=config.name,
            status=status,
            steps=tuple(step_results),
        )

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
            self._record_step_metrics(
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
        self._record_step_metrics(
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

    def _build_skipped_step_result(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig | TransformStepConfig,
        failed_step_id: str,
        context_labels: Mapping[str, str],
    ) -> WorkflowStepExecutionResult:
        step_kind = (
            _STEP_KIND_PIPELINE if isinstance(step, WorkflowStepConfig) else "transform"
        )
        self._record_step_metrics(
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
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig | TransformStepConfig,
        context_labels: Mapping[str, str],
    ) -> WorkflowStepExecutionResult:
        step_kind = (
            _STEP_KIND_PIPELINE if isinstance(step, WorkflowStepConfig) else "transform"
        )
        self._record_step_metrics(
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

    def _record_step_metrics(
        self,
        *,
        workflow_name: str,
        step_kind: str,
        status: str,
        duration_seconds: float,
        context_labels: Mapping[str, str],
    ) -> None:
        self.metrics.increment_counter(
            _WORKFLOW_STEP_EVENTS_TOTAL,
            1,
            {
                "workflow": workflow_name,
                "step_kind": step_kind,
                "status": status,
                **context_labels,
            },
        )
        self.metrics.observe_histogram(
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


def _workflow_status_to_gauge_value(status: str) -> float:
    """Map terminal workflow states onto the canonical L0 severity enum."""
    if status in {"success", "completed"}:
        return 0.0
    if status == "failed":
        return 2.0
    return 1.0
