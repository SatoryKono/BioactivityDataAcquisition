"""Workflow runner service for declarative pipeline and transform DAGs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.services.execution.workflow_runner_step_execution import (
    TransformStepRuntimeOptions,
    apply_workflow_step_transition,
    execute_pipeline_step,
    execute_transform_step,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    attach_workflow_run_report,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    ResolvedWorkflowStepTransitionRecord,
    WorkflowExecutionState,
    build_resume_skipped_step_result,
    build_skipped_step_result,
    record_workflow_pipeline_expected_metrics,
    record_workflow_run_metrics,
    workflow_result_from_state,
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
from bioetl.domain.workflow import (
    WorkflowConfig,
    WorkflowStepConfig,
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
    "WorkflowRunExecutionResult",
    "WorkflowRunnerService",
    "WorkflowStepExecutionResult",
]


@dataclass(slots=True)
class WorkflowRunnerService:
    """Execute workflow pipeline and transform steps in topological order."""

    pipeline_runner: PipelineRunnerService
    transform_service: WorkflowTransformService
    metrics: MetricsPort
    monotonic: Callable[[], float] = perf_counter
    workflow_transform_artifact_sink: WorkflowTransformArtifactSinkProtocol | None = (
        None
    )

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        workflow_run_id: str | None = None,
        manifest_id: str | None = None,
        completed_step_ids: frozenset[str] | None = None,
        completed_transform_fingerprints: dict[str, str] | None = None,
        step_started_callback: Callable[..., None] | None = None,
        step_completed_callback: Callable[[WorkflowStepExecutionResult], None]
        | None = None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ) = None,
        created_at_factory: Callable[[], datetime] | None = None,
    ) -> WorkflowRunExecutionResult:
        """Run a workflow config and stop on first failed step."""
        self.record_expected_pipeline_metrics(config)
        state = WorkflowExecutionState(step_results=[], step_outputs={})
        workflow_context_labels = config.workflow_context_labels
        effective_dry_run = bool(config.defaults.dry_run)
        debug_export_enabled = bool(config.defaults.debug_export_enabled)
        debug_export_dir = config.defaults.debug_export_dir

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
                dry_run=effective_dry_run,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                debug_export=(debug_export_enabled, debug_export_dir),
                created_at_factory=created_at_factory,
            )
            apply_workflow_step_transition(
                state=state,
                step=step,
                transition=transition,
                step_completed_callback=step_completed_callback,
            )

        record_workflow_run_metrics(
            metrics=self.metrics,
            workflow_name=config.name,
            status=state.status,
            context_labels=workflow_context_labels,
        )
        result = workflow_result_from_state(config.name, state)
        result = replace(
            result,
            workflow_run_id=workflow_run_id,
            manifest_id=manifest_id,
        )
        return attach_workflow_run_report(
            config=config,
            result=result,
            logger=getattr(self.pipeline_runner, "logger", None),
        )

    def record_expected_pipeline_metrics(self, config: WorkflowConfig) -> None:
        """Record planned pipeline scopes before workflow step execution."""
        record_workflow_pipeline_expected_metrics(
            metrics=self.metrics,
            config=config,
        )

    async def _resolve_step_transition(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepDefinition,
        state: WorkflowExecutionState,
        workflow_context_labels: Mapping[str, str],
        completed_step_ids: frozenset[str] | None,
        completed_transform_fingerprints: dict[str, str] | None,
        step_started_callback: Callable[..., None] | None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ),
        dry_run: bool,
        workflow_run_id: str | None,
        manifest_id: str | None,
        debug_export: tuple[bool, str | None],
        created_at_factory: Callable[[], datetime] | None,
    ) -> ResolvedWorkflowStepTransitionRecord:
        """Resolve whether a step should run, resume-skip, or failure-skip."""
        debug_export_enabled, debug_export_dir = debug_export
        policy = resolve_step_transition_policy(
            step,
            failed_step_id=state.failed_step_id,
            completed_step_ids=completed_step_ids,
        )
        if policy.disposition == "skip_failed":
            return ResolvedWorkflowStepTransitionRecord(
                policy=policy,
                result=build_skipped_step_result(
                    metrics=self.metrics,
                    workflow_name=workflow_name,
                    step=step,
                    failed_step_id=policy.failed_step_id or "",
                    context_labels=workflow_context_labels,
                ),
            )
        if policy.disposition == "skip_completed":
            return ResolvedWorkflowStepTransitionRecord(
                policy=policy,
                result=build_resume_skipped_step_result(
                    metrics=self.metrics,
                    workflow_name=workflow_name,
                    step=step,
                    context_labels=workflow_context_labels,
                ),
            )
        return ResolvedWorkflowStepTransitionRecord(
            policy=policy,
            result=await self._run_step(
                workflow_name=workflow_name,
                step=step,
                step_outputs=state.step_outputs,
                workflow_context_labels=workflow_context_labels,
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=step_started_callback,
                transform_commit_callback=transform_commit_callback,
                dry_run=dry_run,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                debug_export_enabled=debug_export_enabled,
                debug_export_dir=debug_export_dir,
                created_at_factory=created_at_factory,
            ),
        )

    async def _run_step(
        self,
        *,
        workflow_name: str,
        step: WorkflowStepDefinition,
        step_outputs: dict[str, object],
        workflow_context_labels: Mapping[str, str],
        completed_transform_fingerprints: dict[str, str] | None,
        step_started_callback: Callable[..., None] | None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ),
        dry_run: bool,
        workflow_run_id: str | None,
        manifest_id: str | None,
        debug_export_enabled: bool,
        debug_export_dir: str | None,
        created_at_factory: Callable[[], datetime] | None,
    ) -> WorkflowStepExecutionResult:
        if isinstance(step, WorkflowStepConfig):
            return await execute_pipeline_step(
                pipeline_runner=self.pipeline_runner,
                metrics=self.metrics,
                monotonic=self.monotonic,
                workflow_name=workflow_name,
                step=step,
                workflow_context_labels=workflow_context_labels,
                step_started_callback=step_started_callback,
                workflow_run_id=workflow_run_id,
            )
        return await execute_transform_step(
            transform_service=self.transform_service,
            artifact_sink=self.workflow_transform_artifact_sink,
            workflow_name=workflow_name,
            step=step,
            step_outputs=step_outputs,
            workflow_context_labels=workflow_context_labels,
            options=TransformStepRuntimeOptions(
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=step_started_callback,
                transform_commit_callback=transform_commit_callback,
                dry_run=dry_run,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                debug_export_enabled=debug_export_enabled,
                debug_export_dir=debug_export_dir,
                created_at_factory=created_at_factory,
            ),
        )
