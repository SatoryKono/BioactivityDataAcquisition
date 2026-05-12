"""Workflow execution preparation helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from bioetl.application.services.control_plane.workflow_manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.application.services.control_plane.workflow_manifest_service import (
    WorkflowManifestService,
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
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)

__all__ = ["WorkflowExecutionPreparationResult", "prepare_workflow_execution"]


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPreparationResult:
    """Prepared manifest/state pair and resume cursor for one workflow run."""

    manifest: WorkflowManifest
    state: WorkflowExecutionState
    completed_step_ids: frozenset[str]
    completed_transform_fingerprints: dict[str, str]
    resumed: bool


def prepare_workflow_execution(
    *,
    config: WorkflowConfig,
    launch_context: dict[str, object],
    resume_last: bool,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
    manifest_service: WorkflowManifestService,
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
    if not resume_last:
        return _prepare_new_execution(
            manifest_service=manifest_service,
            workflow_state_port=workflow_state_port,
            request=request,
        )
    return _prepare_resumed_execution(
        config=config,
        current_fingerprint=current_fingerprint,
        force_steps=force_steps,
        repair_steps=repair_steps,
        manifest_service=manifest_service,
        workflow_state_port=workflow_state_port,
        now_factory=now_factory,
    )


def _prepare_new_execution(
    *,
    manifest_service: WorkflowManifestService,
    workflow_state_port: WorkflowExecutionStatePort,
    request: WorkflowManifestCreateSpec,
) -> WorkflowExecutionPreparationResult:
    manifest = manifest_service.create_manifest(request)
    state = _build_initial_state(manifest)
    workflow_state_port.save(state)
    return WorkflowExecutionPreparationResult(
        manifest=manifest,
        state=state,
        completed_step_ids=frozenset(),
        completed_transform_fingerprints={},
        resumed=False,
    )


def _prepare_resumed_execution(
    *,
    config: WorkflowConfig,
    current_fingerprint: str,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
    manifest_service: WorkflowManifestService,
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
) -> WorkflowExecutionPreparationResult:
    latest_state = _load_resume_state(
        workflow_state_port=workflow_state_port,
        workflow_name=config.name,
    )
    _validate_resume_state(
        latest_state=latest_state,
        workflow_name=config.name,
        current_fingerprint=current_fingerprint,
        force_steps=force_steps,
        repair_steps=repair_steps,
    )
    manifest = _load_resume_manifest(
        manifest_service=manifest_service,
        latest_state=latest_state,
    )
    normalized_state = _normalize_resume_state(
        latest_state,
        workflow_state_port=workflow_state_port,
        now_factory=now_factory,
    )
    return WorkflowExecutionPreparationResult(
        manifest=manifest,
        state=normalized_state,
        completed_step_ids=_resolve_skipped_step_ids(
            state=normalized_state,
            force_steps=force_steps,
            repair_steps=repair_steps,
        ),
        completed_transform_fingerprints=_resolve_completed_transform_fingerprints(
            state=normalized_state,
            force_steps=force_steps,
            repair_steps=repair_steps,
        ),
        resumed=True,
    )


def _load_resume_state(
    *,
    workflow_state_port: WorkflowExecutionStatePort,
    workflow_name: str,
) -> WorkflowExecutionState:
    latest_state = workflow_state_port.get_latest(workflow_name)
    if latest_state is None:
        raise RuntimeError(
            f"Workflow '{workflow_name}' has no persisted execution state for --resume-last"
        )
    return latest_state


def _validate_resume_state(
    *,
    latest_state: WorkflowExecutionState,
    workflow_name: str,
    current_fingerprint: str,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> None:
    if latest_state.execution_fingerprint != current_fingerprint:
        raise RuntimeError(
            "Workflow configuration changed since the last execution; "
            "--resume-last requires the same execution fingerprint"
        )
    if latest_state.status == "success":
        raise RuntimeError(
            f"Workflow '{workflow_name}' already completed successfully; nothing to resume"
        )
    if latest_state.repair_required and not (repair_steps or force_steps):
        raise RuntimeError(
            latest_state.repair_hint
            or "Workflow resume requires explicit --repair-steps or --force-steps"
        )


def _load_resume_manifest(
    *,
    manifest_service: WorkflowManifestService,
    latest_state: WorkflowExecutionState,
) -> WorkflowManifest:
    manifest = manifest_service.manifest_port.get(latest_state.manifest_id)
    if manifest is None:
        raise RuntimeError(
            "Workflow resume failed because the persisted manifest could not be loaded"
        )
    return manifest


def _normalize_resume_state(
    latest_state: WorkflowExecutionState,
    *,
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
) -> WorkflowExecutionState:
    if latest_state.status != "running":
        return latest_state
    normalized_state = replace(
        latest_state,
        status="incomplete",
        updated_at=now_factory(),
    )
    workflow_state_port.save(normalized_state)
    return normalized_state


def _resolve_skipped_step_ids(
    *,
    state: WorkflowExecutionState,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> frozenset[str]:
    forced_or_repaired = {*force_steps, *repair_steps}
    return frozenset(
        step.step_id
        for step in state.steps
        if step.status == "success" and step.step_id not in forced_or_repaired
    )


def _resolve_completed_transform_fingerprints(
    *,
    state: WorkflowExecutionState,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> dict[str, str]:
    forced_or_repaired = {*force_steps, *repair_steps}
    return {
        step_id: fingerprint
        for step_id, fingerprint in state.completed_transform_fingerprints.items()
        if step_id not in forced_or_repaired
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


def _apply_incremental_offset(
    *,
    config: WorkflowConfig,
    workflow_state_port: WorkflowExecutionStatePort,
) -> WorkflowConfig:
    """Apply incremental offset from last successful execution.

    Semantics:
    - Loads last state by workflow name
    - Uses offset only if status="success" and both fields are populated
    - Otherwise leaves configuration unchanged (first run or error)
    """
    latest_state = workflow_state_port.get_latest(config.name)
    if latest_state is None:
        return config

    # Use offset only from successful runs
    if latest_state.status != "success":
        return config

    if latest_state.last_start_offset is None or latest_state.last_limit is None:
        return config

    new_offset = latest_state.last_start_offset + latest_state.last_limit
    override = WorkflowRunOptionsConfig(start_offset=new_offset)

    updated_steps = []
    for step in config.steps:
        if isinstance(step, WorkflowStepConfig):
            updated_steps.append(
                replace(
                    step,
                    run_options=step.run_options.merged_with(override),
                )
            )
        else:
            updated_steps.append(step)

    return replace(
        config,
        defaults=config.defaults.merged_with(override),
        steps=tuple(updated_steps),
    )
