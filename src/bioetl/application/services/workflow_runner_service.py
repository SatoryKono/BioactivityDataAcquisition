"""Workflow runner service for declarative pipeline and transform DAGs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformExecutionResult,
    WorkflowTransformService,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
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
_WORKFLOW_STEP_EVENTS_TOTAL = "bioetl_workflow_step_events_total"
_STEP_KIND_PIPELINE = "pipeline"


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

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        completed_transform_fingerprints: dict[str, str] | None = None,
    ) -> WorkflowRunExecutionResult:
        """Run a workflow config and stop on first failed step."""
        step_results: list[WorkflowStepExecutionResult] = []
        step_outputs: dict[str, object] = {}
        status = "success"

        for step_id in config.topological_step_ids:
            step = config.get_step(step_id)
            if step is None:
                continue
            result = await self._run_step(
                workflow_name=config.name,
                step=step,
                step_outputs=step_outputs,
                completed_transform_fingerprints=completed_transform_fingerprints,
            )
            step_results.append(result)
            step_outputs[step.step_id] = result.payload
            if result.status == "failed":
                status = "failed"
                break

        self.metrics.increment_counter(
            _WORKFLOW_RUNS_TOTAL,
            1,
            {"workflow": config.name, "status": status},
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
        completed_transform_fingerprints: dict[str, str] | None,
    ) -> WorkflowStepExecutionResult:
        if isinstance(step, WorkflowStepConfig):
            return await self._run_pipeline_step(workflow_name=workflow_name, step=step)
        return await self._run_transform_step(
            workflow_name=workflow_name,
            step=step,
            step_outputs=step_outputs,
            completed_transform_fingerprints=completed_transform_fingerprints,
        )

    async def _run_pipeline_step(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepConfig,
    ) -> WorkflowStepExecutionResult:
        try:
            result = await self.pipeline_runner.run(
                step.pipeline_name,
                options=_run_options_from_config(step.run_options),
            )
        except Exception as exc:
            self._record_pipeline_step(workflow_name=workflow_name, status="failed")
            return WorkflowStepExecutionResult(
                step_id=step.step_id,
                step_kind=_STEP_KIND_PIPELINE,
                status="failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        status = "success" if result.is_success else "failed"
        self._record_pipeline_step(workflow_name=workflow_name, status=status)
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
        completed_transform_fingerprints: dict[str, str] | None,
    ) -> WorkflowStepExecutionResult:
        upstream_outputs = {
            dependency: step_outputs[dependency]
            for dependency in step.depends_on
            if dependency in step_outputs
        }
        result = await self.transform_service.run_step(
            workflow_name=workflow_name,
            step=step,
            upstream_outputs=upstream_outputs,
            completed_fingerprints=completed_transform_fingerprints,
        )
        return _step_result_from_transform_result(result)

    def _record_pipeline_step(self, *, workflow_name: str, status: str) -> None:
        self.metrics.increment_counter(
            _WORKFLOW_STEP_EVENTS_TOTAL,
            1,
            {
                "workflow": workflow_name,
                "step_kind": _STEP_KIND_PIPELINE,
                "status": status,
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
