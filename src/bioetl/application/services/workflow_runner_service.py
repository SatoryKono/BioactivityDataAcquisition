"""Workflow runner service for declarative pipeline and transform DAGs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.services.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow_runner_support import (
    ResolvedWorkflowStepTransitionRecord,
    WorkflowExecutionState,
    build_resume_skipped_step_result,
    build_skipped_step_result,
    record_step_metrics,
    record_workflow_run_metrics,
    run_options_from_config,
    step_result_from_transform_result,
    workflow_result_from_state,
)
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformDestructiveCommit,
    WorkflowTransformService,
)
from bioetl.application.services.workflow_transition_policy import (
    WorkflowStepDefinition,
    apply_step_result_transition,
    resolve_step_transition_policy,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
    WorkflowTransformSpec,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.workflow_transform_artifacts import (
        WorkflowTransformArtifactSinkProtocol,
    )
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "WorkflowRunExecutionResult",
    "WorkflowRunnerService",
    "WorkflowStepExecutionResult",
]

_STEP_KIND_PIPELINE = "pipeline"
_WORKFLOW_STEP_FAILURES = (
    BioETLError,
    KeyError,
    RuntimeError,
    TypeError,
    ValueError,
)


@dataclass(slots=True)
class WorkflowRunnerService:
    """Execute workflow pipeline and transform steps in topological order."""

    pipeline_runner: PipelineRunnerService
    transform_service: WorkflowTransformService
    metrics: MetricsPort
    monotonic: Callable[[], float] = perf_counter
    workflow_transform_artifact_sink: WorkflowTransformArtifactSinkProtocol | None = None

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
                debug_export_enabled=debug_export_enabled,
                debug_export_dir=debug_export_dir,
                created_at_factory=created_at_factory,
            )
            self._apply_step_transition(
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
        return workflow_result_from_state(config.name, state)

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
        debug_export_enabled: bool,
        debug_export_dir: str | None,
        created_at_factory: Callable[[], datetime] | None,
    ) -> ResolvedWorkflowStepTransitionRecord:
        """Resolve whether a step should run, resume-skip, or failure-skip."""
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

    def _apply_step_transition(
        self,
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
            dry_run=dry_run,
            workflow_run_id=workflow_run_id,
            manifest_id=manifest_id,
            debug_export_enabled=debug_export_enabled,
            debug_export_dir=debug_export_dir,
            created_at_factory=created_at_factory,
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
            step_options = replace(
                run_options_from_config(step.run_options),
                workflow_id=workflow_name,
            )
            result = await self.pipeline_runner.run(
                step.pipeline_name,
                options=step_options,
            )
        except _WORKFLOW_STEP_FAILURES as exc:
            record_step_metrics(
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
        record_step_metrics(
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
        dry_run: bool,
        workflow_run_id: str | None,
        manifest_id: str | None,
        debug_export_enabled: bool,
        debug_export_dir: str | None,
        created_at_factory: Callable[[], datetime] | None,
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
            dry_run=dry_run,
            workflow_run_id=workflow_run_id,
            manifest_id=manifest_id,
            debug_export_enabled=debug_export_enabled,
            debug_export_dir=debug_export_dir,
            artifact_sink=self.workflow_transform_artifact_sink,
            created_at=created_at_factory() if created_at_factory is not None else None,
            destructive_commit_callback=transform_commit_callback,
        )
        return step_result_from_transform_result(result)
