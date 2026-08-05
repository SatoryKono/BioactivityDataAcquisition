"""Step-level execution helpers for WorkflowRunnerService."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    ResolvedWorkflowStepTransitionRecord,
    WorkflowExecutionState,
    record_step_metrics,
    run_options_from_config,
    step_result_from_transform_result,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformDestructiveCommit as WorkflowTransformDestructiveCommit,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.services.workflow.workflow_transition_policy import (
    WorkflowStepDefinition,
    apply_step_result_transition,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowStepConfig,
    WorkflowTransformSpec,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.workflow.workflow_transform_artifacts import (
        WorkflowTransformArtifactSinkProtocol,
    )
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "TransformStepRuntimeOptions",
    "apply_workflow_step_transition",
    "execute_pipeline_step",
    "execute_transform_step",
]

_STEP_KIND_PIPELINE = "pipeline"
_WORKFLOW_STEP_FAILURES = (
    AttributeError,
    BioETLError,
    KeyError,
    RuntimeError,
    TypeError,
    ValueError,
)


def optional_identity(value: object, field_name: str) -> str | None:
    """Return a stable child identity exposed by a result or typed failure."""
    raw_identity = getattr(value, field_name, None)
    return str(raw_identity) if raw_identity is not None else None


def apply_workflow_step_transition(
    *,
    state: WorkflowExecutionState,
    step: WorkflowStepDefinition,
    transition: ResolvedWorkflowStepTransitionRecord,
    step_completed_callback: Callable[[WorkflowStepExecutionResult], None] | None,
) -> None:
    """Apply one resolved transition to mutable workflow execution state."""
    result = transition.result
    state.step_results.append(result)
    if step_completed_callback is not None:
        step_completed_callback(result)
    if transition.policy.stores_output:
        state.step_outputs[step.step_id] = result.payload
    state.status, state.failed_step_id = apply_step_result_transition(
        step=step,
        result_status=result.status,
        workflow_status=state.status,
        failed_step_id=state.failed_step_id,
    )


async def execute_pipeline_step(
    *,
    pipeline_runner: PipelineRunnerService,
    metrics: MetricsPort,
    monotonic: Callable[[], float],
    workflow_name: str,
    step: WorkflowStepConfig,
    workflow_context_labels: Mapping[str, str],
    step_started_callback: Callable[..., None] | None,
    workflow_run_id: str | None,
) -> WorkflowStepExecutionResult:
    """Run one pipeline step and project step-level metrics."""
    if step_started_callback is not None:
        step_started_callback(step, fingerprint=None)
    started = monotonic()
    try:
        step_options = replace(
            run_options_from_config(step.run_options),
            workflow_id=workflow_name,
            workflow_run_id=workflow_run_id,
            workflow_name=workflow_name,
            workflow_step_id=step.step_id,
        )
        result = await pipeline_runner.run(
            step.pipeline_name,
            options=step_options,
        )
    except _WORKFLOW_STEP_FAILURES as exc:
        record_step_metrics(
            metrics=metrics,
            workflow_name=workflow_name,
            step_kind=_STEP_KIND_PIPELINE,
            status="failed",
            duration_seconds=monotonic() - started,
            context_labels=workflow_context_labels,
        )
        return WorkflowStepExecutionResult(
            step_id=step.step_id,
            step_kind=_STEP_KIND_PIPELINE,
            status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
            child_run_id=optional_identity(exc, "run_id"),
            child_manifest_id=optional_identity(exc, "manifest_id"),
        )
    status = "success" if result.is_success else "failed"
    record_step_metrics(
        metrics=metrics,
        workflow_name=workflow_name,
        step_kind=_STEP_KIND_PIPELINE,
        status=status,
        duration_seconds=monotonic() - started,
        context_labels=workflow_context_labels,
    )
    return WorkflowStepExecutionResult(
        step_id=step.step_id,
        step_kind=_STEP_KIND_PIPELINE,
        status=status,
        payload=result,
        error_type=getattr(result, "error_type", None),
        error_message=getattr(result, "error_message", None),
        child_run_id=optional_identity(result, "run_id"),
        child_manifest_id=optional_identity(result, "manifest_id"),
    )


@dataclass(frozen=True, slots=True)
class TransformStepRuntimeOptions:
    """Packed transform-step runtime options (python:S107)."""

    completed_transform_fingerprints: dict[str, str] | None
    step_started_callback: Callable[..., None] | None
    transform_commit_callback: (
        Callable[[WorkflowTransformDestructiveCommit], None] | None
    )
    dry_run: bool
    workflow_run_id: str | None
    manifest_id: str | None
    debug_export_enabled: bool
    debug_export_dir: str | None
    created_at_factory: Callable[[], datetime] | None


async def execute_transform_step(
    *,
    transform_service: WorkflowTransformService,
    artifact_sink: WorkflowTransformArtifactSinkProtocol | None,
    workflow_name: str,
    step: TransformStepConfig,
    step_outputs: dict[str, object],
    workflow_context_labels: Mapping[str, str],
    options: TransformStepRuntimeOptions,
) -> WorkflowStepExecutionResult:
    """Run one transform step through the workflow transform service."""
    spec = WorkflowTransformSpec.from_step(step)
    if options.step_started_callback is not None:
        options.step_started_callback(step, fingerprint=spec.fingerprint)
    upstream_outputs = {
        dependency: step_outputs[dependency]
        for dependency in step.depends_on
        if dependency in step_outputs
    }
    created_at = (
        options.created_at_factory() if options.created_at_factory is not None else None
    )
    result = await transform_service.run_step(
        workflow_name=workflow_name,
        step=step,
        upstream_outputs=upstream_outputs,
        context_labels=workflow_context_labels,
        completed_fingerprints=options.completed_transform_fingerprints,
        dry_run=options.dry_run,
        workflow_run_id=options.workflow_run_id,
        manifest_id=options.manifest_id,
        debug_export_enabled=options.debug_export_enabled,
        debug_export_dir=options.debug_export_dir,
        artifact_sink=artifact_sink,
        created_at=created_at,
        destructive_commit_callback=options.transform_commit_callback,
    )
    return step_result_from_transform_result(result)
