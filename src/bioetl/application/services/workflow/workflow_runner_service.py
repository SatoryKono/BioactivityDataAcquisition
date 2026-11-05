"""Workflow runner service for declarative pipeline and transform DAGs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.execution.workflow_runner_step_execution import (
    apply_workflow_step_transition,
)
from bioetl.application.services.workflow.workflow_runner_finalize import (
    WorkflowFinalizeContext,
    finalize_workflow_run_result,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    WorkflowExecutionState,
    record_workflow_pipeline_expected_metrics,
)
from bioetl.application.services.workflow.workflow_runner_transitions import (
    WorkflowStepTransitionContext,
    WorkflowStepTransitionServices,
    resolve_workflow_step_transition,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformDestructiveCommit as WorkflowTransformDestructiveCommit,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.domain.ports import RunReportStorePort
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


def _cohort_producer_ids(config: WorkflowConfig) -> set[str]:
    """Return producer and consumer IDs whose snapshots are needed for cohorts."""
    producers = {
        step.reference_cohort.step_id
        for step in config.pipeline_steps
        if step.reference_cohort is not None
    }
    producers.update(
        step.step_id
        for step in config.pipeline_steps
        if step.reference_cohort is not None
    )
    return producers


@dataclass(slots=True)
class WorkflowRunnerService:
    """Execute workflow pipeline and transform steps in topological order."""

    pipeline_runner: PipelineRunnerService
    transform_service: WorkflowTransformService
    metrics: MetricsPort
    report_store: RunReportStorePort
    monotonic: Callable[[], float] = perf_counter
    workflow_transform_artifact_sink: WorkflowTransformArtifactSinkProtocol | None = (
        None
    )
    report_root: Path | None = None
    cohort_resolver: (
        Callable[
            [WorkflowStepConfig, Mapping[str, object]], Awaitable[WorkflowStepConfig]
        ]
        | None
    ) = None
    # RF-004: Composition-injected finalize consistency check (soft diagnostics).
    evidence_location_verify: Callable[[WorkflowRunExecutionResult], None] | None = None

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        workflow_run_id: str | None = None,
        manifest_id: str | None = None,
        execution_fingerprint: str | None = None,
        resumed: bool = False,
        completed_step_ids: frozenset[str] | None = None,
        completed_transform_fingerprints: dict[str, str] | None = None,
        step_started_callback: Callable[..., None] | None = None,
        step_completed_callback: Callable[[WorkflowStepExecutionResult], None]
        | None = None,
        transform_commit_callback: (
            Callable[[WorkflowTransformDestructiveCommit], None] | None
        ) = None,
        created_at_factory: Callable[[], datetime] | None = None,
        restored_step_outputs: Mapping[str, object] | None = None,
    ) -> WorkflowRunExecutionResult:
        """Run a workflow config; a failed step only skips steps that depend on it.

        Independent steps still run; steps declaring a failed (or blocked) step
        in ``depends_on`` are failure-skipped instead of executed.
        """
        started_at = current_utc_time()
        started_monotonic = perf_counter()
        self.record_expected_pipeline_metrics(config)
        state = WorkflowExecutionState(
            step_results=[], step_outputs=dict(restored_step_outputs or {})
        )
        workflow_context_labels = config.workflow_context_labels
        effective_dry_run = bool(config.defaults.dry_run)
        debug_export_enabled = bool(config.defaults.debug_export_enabled)
        debug_export_dir = config.defaults.debug_export_dir
        cohort_producers = _cohort_producer_ids(config)

        transition_services = WorkflowStepTransitionServices(
            pipeline_runner=self.pipeline_runner,
            transform_service=self.transform_service,
            metrics=self.metrics,
            monotonic=self.monotonic,
            cohort_resolver=self.cohort_resolver,
            artifact_sink=self.workflow_transform_artifact_sink,
        )
        for step_id in config.topological_step_ids:
            step = config.get_step(step_id)
            if step is None:
                continue
            transition = await resolve_workflow_step_transition(
                WorkflowStepTransitionContext(
                    services=transition_services,
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
                    capture_producer_snapshot=step_id in cohort_producers,
                )
            )
            apply_workflow_step_transition(
                state=state,
                step=step,
                transition=transition,
                step_completed_callback=step_completed_callback,
            )

        return finalize_workflow_run_result(
            WorkflowFinalizeContext(
                config=config,
                state=state,
                workflow_context_labels=workflow_context_labels,
                workflow_run_id=workflow_run_id,
                manifest_id=manifest_id,
                execution_fingerprint=execution_fingerprint,
                resumed=resumed,
                started_at=started_at,
                started_monotonic=started_monotonic,
                metrics=self.metrics,
                report_store=self.report_store,
                report_root=self.report_root,
                logger=getattr(self.pipeline_runner, "logger", None),
                archive_control_plane=getattr(
                    self.pipeline_runner, "archive_control_plane", None
                ),
                evidence_location_verify=self.evidence_location_verify,
            )
        )

    def record_expected_pipeline_metrics(self, config: WorkflowConfig) -> None:
        """Record planned pipeline scopes before workflow step execution."""
        record_workflow_pipeline_expected_metrics(
            metrics=self.metrics,
            config=config,
        )
