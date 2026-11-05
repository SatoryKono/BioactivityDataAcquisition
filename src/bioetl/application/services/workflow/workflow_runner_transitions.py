"""Step transition resolution for WorkflowRunnerService."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.execution.workflow_runner_step_execution import (
    TransformStepRuntimeOptions,
    execute_pipeline_step,
    execute_transform_step,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    ResolvedWorkflowStepTransitionRecord,
    WorkflowExecutionState,
    build_resume_skipped_step_result,
    build_skipped_step_result,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformDestructiveCommit as WorkflowTransformDestructiveCommit,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.services.workflow.workflow_transition_policy import (
    WorkflowStepDefinition,
    resolve_step_transition_policy,
)
from bioetl.domain.workflow import WorkflowStepConfig

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.workflow.workflow_transform_artifacts import (
        WorkflowTransformArtifactSinkProtocol,
    )
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "WorkflowStepTransitionContext",
    "blocked_step_ids",
    "resolve_workflow_step_transition",
]


@dataclass(frozen=True, slots=True)
class WorkflowStepTransitionServices:
    """Injected collaborators for step transition resolution (python:S107)."""

    pipeline_runner: PipelineRunnerService
    transform_service: WorkflowTransformService
    metrics: MetricsPort
    monotonic: Callable[[], float]
    cohort_resolver: (
        Callable[
            [WorkflowStepConfig, Mapping[str, object]], Awaitable[WorkflowStepConfig]
        ]
        | None
    )
    artifact_sink: WorkflowTransformArtifactSinkProtocol | None


@dataclass(frozen=True, slots=True)
class WorkflowStepTransitionContext:
    """Per-step transition request payload (python:S107)."""

    services: WorkflowStepTransitionServices
    workflow_name: str
    step: WorkflowStepDefinition
    state: WorkflowExecutionState
    workflow_context_labels: Mapping[str, str]
    completed_step_ids: frozenset[str] | None
    completed_transform_fingerprints: dict[str, str] | None
    step_started_callback: Callable[..., None] | None
    transform_commit_callback: (
        Callable[[WorkflowTransformDestructiveCommit], None] | None
    )
    dry_run: bool
    workflow_run_id: str | None
    manifest_id: str | None
    debug_export: tuple[bool, str | None]
    created_at_factory: Callable[[], datetime] | None
    capture_producer_snapshot: bool = False


def blocked_step_ids(state: WorkflowExecutionState) -> frozenset[str]:
    """Return steps whose failure or failure-skip must block dependents."""
    blocked = {
        result.step_id
        for result in state.step_results
        if result.status == "failed"
        or (result.status == "skipped" and result.error_type == "UpstreamStepFailed")
    }
    if state.failed_step_id is not None:
        blocked.add(state.failed_step_id)
    return frozenset(blocked)


async def resolve_workflow_step_transition(
    context: WorkflowStepTransitionContext,
) -> ResolvedWorkflowStepTransitionRecord:
    """Resolve whether a step should run, resume-skip, or failure-skip."""
    services = context.services
    step = context.step
    state = context.state
    debug_export_enabled, debug_export_dir = context.debug_export
    policy = resolve_step_transition_policy(
        step,
        failed_step_id=state.failed_step_id,
        completed_step_ids=context.completed_step_ids,
        blocked_step_ids=blocked_step_ids(state),
    )
    if policy.disposition == "skip_failed":
        return ResolvedWorkflowStepTransitionRecord(
            policy=policy,
            result=build_skipped_step_result(
                metrics=services.metrics,
                workflow_name=context.workflow_name,
                step=step,
                failed_step_id=policy.failed_step_id or "",
                context_labels=context.workflow_context_labels,
            ),
        )
    if policy.disposition == "skip_completed":
        completed = build_resume_skipped_step_result(
            metrics=services.metrics,
            workflow_name=context.workflow_name,
            step=step,
            context_labels=context.workflow_context_labels,
        )
        restored = state.step_outputs.get(step.step_id)
        if isinstance(restored, Mapping):
            run_id = restored.get("run_id")
            child_manifest = restored.get("manifest_id")
            completed = replace(
                completed,
                payload=restored,
                child_run_id=str(run_id) if run_id is not None else None,
                child_manifest_id=str(child_manifest)
                if child_manifest is not None
                else None,
            )
        return ResolvedWorkflowStepTransitionRecord(
            policy=policy,
            result=completed,
        )
    return ResolvedWorkflowStepTransitionRecord(
        policy=policy,
        result=await _execute_resolved_step(
            services=services,
            workflow_name=context.workflow_name,
            step=step,
            step_outputs=state.step_outputs,
            workflow_context_labels=context.workflow_context_labels,
            options=TransformStepRuntimeOptions(
                completed_transform_fingerprints=context.completed_transform_fingerprints,
                step_started_callback=context.step_started_callback,
                transform_commit_callback=context.transform_commit_callback,
                dry_run=context.dry_run,
                workflow_run_id=context.workflow_run_id,
                manifest_id=context.manifest_id,
                debug_export_enabled=debug_export_enabled,
                debug_export_dir=debug_export_dir,
                created_at_factory=context.created_at_factory,
            ),
            capture_producer_snapshot=context.capture_producer_snapshot,
        ),
    )


async def _execute_resolved_step(
    *,
    services: WorkflowStepTransitionServices,
    workflow_name: str,
    step: WorkflowStepDefinition,
    step_outputs: dict[str, object],
    workflow_context_labels: Mapping[str, str],
    options: TransformStepRuntimeOptions,
    capture_producer_snapshot: bool,
) -> WorkflowStepExecutionResult:
    if isinstance(step, WorkflowStepConfig):
        return await execute_pipeline_step(
            pipeline_runner=services.pipeline_runner,
            cohort_resolver=services.cohort_resolver,
            upstream_outputs=step_outputs,
            capture_producer_snapshot=capture_producer_snapshot,
            metrics=services.metrics,
            monotonic=services.monotonic,
            workflow_name=workflow_name,
            step=step,
            workflow_context_labels=workflow_context_labels,
            step_started_callback=options.step_started_callback,
            workflow_run_id=options.workflow_run_id,
            snapshot_reader=getattr(
                getattr(services.transform_service, "registry", None),
                "snapshot_reader",
                None,
            ),
        )
    return await execute_transform_step(
        transform_service=services.transform_service,
        artifact_sink=services.artifact_sink,
        workflow_name=workflow_name,
        step=step,
        step_outputs=step_outputs,
        workflow_context_labels=workflow_context_labels,
        options=options,
    )
