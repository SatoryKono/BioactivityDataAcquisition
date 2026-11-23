"""Workflow-owned execution preparation helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from bioetl.application.services.control_plane.workflow.manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.application.services.workflow.control_plane._execution_resume_support import (
    load_resume_manifest,
    load_resume_state,
    normalize_resume_state,
    resolve_completed_transform_fingerprints,
    resolve_skipped_step_ids,
    validate_resume_state,
)
from bioetl.application.services.workflow.control_plane.execution_preparation_incremental import (
    _apply_incremental_offset,
    _workflow_step_with_start_offset,
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
    WorkflowStepConfig,
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
    manifest_service: Any,  # Any: dynamic service to avoid circular import
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
    run_id_factory: Callable[[], RunID],
    incremental: bool = False,
) -> WorkflowExecutionPreparationResult:
    """Prepare manifest, execution state, and resume cursor."""
    # Apply incremental offset only for genuinely new executions (not resume).
    # Resume paths must keep the stored offset/fingerprint from prior state.
    is_resume = bool(resume_last or resume_manifest_id or resume_run_id)
    if incremental and not is_resume:
        config = _apply_incremental_offset(
            config=config,
            workflow_state_port=workflow_state_port,
        )
    request = WorkflowManifestCreateSpec(
        workflow_run_id=run_id_factory(),
        config=config,
        launch_context=launch_context,
    )
    if not (resume_last or resume_manifest_id or resume_run_id):
        return _prepare_new_execution(
            manifest_service=manifest_service,
            workflow_state_port=workflow_state_port,
            request=request,
        )
    return _prepare_resumed_execution(
        config=config,
        request=request,
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
    manifest_service: Any,  # Any: dynamic service to avoid circular import
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
    request: WorkflowManifestCreateSpec,
    resume_manifest_id: str | None,
    resume_run_id: RunID | str | None,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
    manifest_service: Any,  # Any: dynamic service to avoid circular import
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
) -> WorkflowExecutionPreparationResult:
    latest_state = load_resume_state(
        workflow_state_port=workflow_state_port,
        workflow_name=config.name,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
    )
    manifest = load_resume_manifest(
        manifest_service=manifest_service,
        latest_state=latest_state,
    )
    config = _restore_pinned_offset(config, manifest)
    current_fingerprint = manifest_service.compute_execution_fingerprint(
        replace(request, config=config)
    )
    if "start_offset" not in manifest.defaults and (
        config.defaults.start_offset is not None
        or current_fingerprint != latest_state.execution_fingerprint
    ):
        raise RuntimeError(
            "Workflow resume failed: manifest has no pinned start_offset "
            "and the execution fingerprint does not match"
        )
    validate_resume_state(
        latest_state=latest_state,
        workflow_name=config.name,
        current_fingerprint=current_fingerprint,
        force_steps=force_steps,
        repair_steps=repair_steps,
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


def _restore_pinned_offset(
    config: WorkflowConfig, manifest: WorkflowManifest
) -> WorkflowConfig:
    if "start_offset" not in manifest.defaults:
        return config
    pinned_offset = manifest.defaults["start_offset"]
    if type(pinned_offset) is not int or pinned_offset < 0:
        raise RuntimeError(
            "Workflow resume failed: manifest has invalid pinned start_offset"
        )
    pinned_steps = _pinned_step_ids(manifest, pinned_offset)
    inherited_offset = config.defaults.start_offset
    return replace(
        config,
        defaults=replace(config.defaults, start_offset=pinned_offset),
        steps=tuple(
            _workflow_step_with_start_offset(step, pinned_offset)
            if isinstance(step, WorkflowStepConfig)
            and step.run_options.start_offset in (None, inherited_offset)
            and step.step_id in pinned_steps
            else step
            for step in config.steps
        ),
    )


def _pinned_step_ids(manifest: WorkflowManifest, offset: int) -> set[str]:
    return {
        step.step_id
        for step in manifest.steps
        if step.run_options is not None
        and step.run_options.get("start_offset") == offset
    }


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
