"""Workflow execution preparation helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from bioetl.application.services.control_plane.workflow._execution_resume_support import (
    load_resume_manifest,
    load_resume_state,
    normalize_resume_state,
    resolve_completed_transform_fingerprints,
    resolve_skipped_step_ids,
    validate_resume_state,
)
from bioetl.application.services.control_plane.workflow.execution_preparation_incremental import (
    _apply_incremental_offset,
)
from bioetl.application.services.control_plane.workflow.manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.domain.control_plane import (
    WorkflowExecutionState,
    WorkflowManifest,
    WorkflowStepState,
)
from bioetl.domain.ports import WorkflowExecutionStatePort
from bioetl.domain.types import RunID
from bioetl.domain.workflow import (
    WorkflowConfig,
)

__all__ = ["WorkflowExecutionPreparationResult", "prepare_workflow_execution"]


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPreparationResult:
    """Prepared manifest/state pair and resume cursor for one workflow run."""

    manifest: WorkflowManifest
    state: WorkflowExecutionState
    config: WorkflowConfig
    completed_step_ids: frozenset[str]
    completed_transform_fingerprints: dict[str, str]
    resumed: bool


def prepare_workflow_execution(
    *,
    config: WorkflowConfig,
    launch_context: dict[str, object],
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: RunID | str | None,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
    manifest_service: "WorkflowManifestService",
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
    run_id_factory: Callable[[], RunID],
    incremental: bool = False,
) -> WorkflowExecutionPreparationResult:
    """Prepare manifest, execution state, and resume cursor."""
    # Apply incremental offset before creating request so fingerprint
    # includes the new start_offset
    if incremental and not resume_last:
        config = _apply_incremental_offset(
            config=config,
            workflow_state_port=workflow_state_port,
        )
    request = WorkflowManifestCreateSpec(
        workflow_run_id=run_id_factory(),
        config=config,
        launch_context=launch_context,
    )
    current_fingerprint = manifest_service.compute_execution_fingerprint(request)
    if not (resume_last or resume_manifest_id or resume_run_id):
        return _prepare_new_execution(
            manifest_service=manifest_service,
            workflow_state_port=workflow_state_port,
            request=request,
        )
    return _prepare_resumed_execution(
        config=config,
        current_fingerprint=current_fingerprint,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
        force_steps=force_steps,
        repair_steps=repair_steps,
        manifest_service=manifest_service,
        workflow_state_port=workflow_state_port,
        now_factory=now_factory,
    )


def _prepare_new_execution(
    *,
    manifest_service: "WorkflowManifestService",
    workflow_state_port: WorkflowExecutionStatePort,
    request: WorkflowManifestCreateSpec,
) -> WorkflowExecutionPreparationResult:
    manifest = manifest_service.create_manifest(request)
    state = _build_initial_state(manifest)
    workflow_state_port.save(state)
    return WorkflowExecutionPreparationResult(
        manifest=manifest,
        state=state,
        config=request.config,
        completed_step_ids=frozenset(),
        completed_transform_fingerprints={},
        resumed=False,
    )


def _prepare_resumed_execution(
    *,
    config: WorkflowConfig,
    current_fingerprint: str,
    resume_manifest_id: str | None,
    resume_run_id: RunID | str | None,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
    manifest_service: "WorkflowManifestService",
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
) -> WorkflowExecutionPreparationResult:
    latest_state = load_resume_state(
        workflow_state_port=workflow_state_port,
        workflow_name=config.name,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
    )
    validate_resume_state(
        latest_state=latest_state,
        workflow_name=config.name,
        current_fingerprint=current_fingerprint,
        force_steps=force_steps,
        repair_steps=repair_steps,
    )
    manifest = load_resume_manifest(
        manifest_service=manifest_service,
        latest_state=latest_state,
    )
    normalized_state = normalize_resume_state(
        latest_state,
        workflow_state_port=workflow_state_port,
        now_factory=now_factory,
    )
    return WorkflowExecutionPreparationResult(
        manifest=manifest,
        state=normalized_state,
        config=config,
        completed_step_ids=resolve_skipped_step_ids(
            state=normalized_state,
            force_steps=force_steps,
            repair_steps=repair_steps,
        ),
        completed_transform_fingerprints=resolve_completed_transform_fingerprints(
            state=normalized_state,
            force_steps=force_steps,
            repair_steps=repair_steps,
        ),
        resumed=True,
    )

def _build_initial_state(manifest: WorkflowManifest) -> WorkflowExecutionState:
    now = manifest.created_at
    steps = tuple(
        WorkflowStepState(
            step_id=step.step_id,
            step_kind=step.kind,
            status="pending",
        )
        for step in manifest.steps
    )
    return WorkflowExecutionState(
        workflow_run_id=manifest.workflow_run_id,
        manifest_id=manifest.manifest_id,
        workflow_name=manifest.workflow_name,
        execution_fingerprint=manifest.execution_fingerprint,
        status="created",
        started_at=now,
        updated_at=now,
        completed_at=None,
        selected_step_ids=manifest.selected_step_ids,
        steps=steps,
        completed_transform_fingerprints={},
    )
