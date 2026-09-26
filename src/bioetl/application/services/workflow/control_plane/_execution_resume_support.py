"""Workflow-owned resume-state helpers for execution preparation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowManifest
from bioetl.domain.ports import WorkflowExecutionStatePort
from bioetl.domain.types import RunID


class _WorkflowManifestPort(Protocol):
    def get(self, manifest_id: str) -> WorkflowManifest | None: ...


class _WorkflowManifestService(Protocol):
    @property
    def manifest_port(self) -> _WorkflowManifestPort: ...


__all__ = [
    "coerce_resume_run_id",
    "load_resume_manifest",
    "load_resume_state",
    "normalize_resume_state",
    "resolve_completed_transform_fingerprints",
    "resolve_skipped_step_ids",
    "validate_resume_state",
]


def load_resume_state(
    *,
    workflow_state_port: WorkflowExecutionStatePort,
    workflow_name: str,
    resume_manifest_id: str | None,
    resume_run_id: RunID | str | None,
) -> WorkflowExecutionState:
    if resume_run_id is not None:
        resolved_run_id = coerce_resume_run_id(resume_run_id)
        state = workflow_state_port.get_by_run_id(resolved_run_id)
        if state is None:
            raise RuntimeError(
                f"Workflow '{workflow_name}' has no persisted execution state for "
                f"--resume-run-id={resolved_run_id}"
            )
        return state
    if resume_manifest_id is not None:
        state = workflow_state_port.get_by_manifest_id(resume_manifest_id)
        if state is None:
            raise RuntimeError(
                f"Workflow '{workflow_name}' has no persisted execution state for "
                f"--resume-manifest-id={resume_manifest_id}"
            )
        return state
    latest_state = workflow_state_port.get_latest(workflow_name)
    if latest_state is None:
        raise RuntimeError(
            f"Workflow '{workflow_name}' has no persisted execution state for --resume-last"
        )
    return latest_state


def coerce_resume_run_id(resume_run_id: RunID | str) -> RunID:
    if isinstance(resume_run_id, UUID):
        return RunID(resume_run_id)
    return RunID(UUID(str(resume_run_id)))


def validate_resume_state(
    *,
    latest_state: WorkflowExecutionState,
    workflow_name: str,
    current_fingerprint: str,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> None:
    _validate_workflow_name(latest_state, workflow_name)
    _validate_identity_fields(latest_state)
    step_ids = _validate_step_integrity(latest_state)
    _validate_step_references(latest_state, step_ids)
    _validate_lifecycle_status(latest_state)
    _validate_execution_fingerprint(latest_state, current_fingerprint)
    _validate_completion_status(latest_state, workflow_name)
    _validate_repair_requirements(latest_state, repair_steps, force_steps)


def _validate_workflow_name(
    latest_state: WorkflowExecutionState, workflow_name: str
) -> None:
    if latest_state.workflow_name != workflow_name:
        raise RuntimeError(
            "Workflow resume state belongs to a different workflow: "
            f"expected {workflow_name!r}, got {latest_state.workflow_name!r}"
        )


def _validate_identity_fields(latest_state: WorkflowExecutionState) -> None:
    if (
        not latest_state.manifest_id.strip()
        or not latest_state.execution_fingerprint.strip()
    ):
        raise RuntimeError(
            "Workflow resume state is damaged: identity fields are missing"
        )


def _validate_step_integrity(latest_state: WorkflowExecutionState) -> tuple[str, ...]:
    step_ids = tuple(step.step_id for step in latest_state.steps)
    if (
        not step_ids
        or any(not str(step_id).strip() for step_id in step_ids)
        or len(step_ids) != len(set(step_ids))
    ):
        raise RuntimeError(
            "Workflow resume state is damaged: step identities are missing or duplicated"
        )
    return step_ids


def _validate_step_references(
    latest_state: WorkflowExecutionState, step_ids: tuple[str, ...]
) -> None:
    unknown_selected = set(latest_state.selected_step_ids).difference(step_ids)
    unknown_completed = set(latest_state.completed_transform_fingerprints).difference(
        step_ids
    )
    if unknown_selected or unknown_completed:
        raise RuntimeError(
            "Workflow resume state is damaged: persisted step references are inconsistent"
        )


def _validate_lifecycle_status(latest_state: WorkflowExecutionState) -> None:
    allowed_statuses = {"created", "running", "incomplete", "failed", "success"}
    if latest_state.status not in allowed_statuses or any(
        step.status not in {"pending", "running", "success", "failed"}
        for step in latest_state.steps
    ):
        raise RuntimeError("Workflow resume state is damaged: unknown lifecycle status")


def _validate_execution_fingerprint(
    latest_state: WorkflowExecutionState, current_fingerprint: str
) -> None:
    if latest_state.execution_fingerprint != current_fingerprint:
        raise RuntimeError(
            "Workflow configuration changed since the last execution; "
            "--resume-last requires the same execution fingerprint"
        )


def _validate_completion_status(
    latest_state: WorkflowExecutionState, workflow_name: str
) -> None:
    """Reject resume if workflow already completed successfully."""
    if latest_state.status == "success":
        raise RuntimeError(
            f"Workflow '{workflow_name}' already completed successfully; nothing to resume"
        )


def _validate_repair_requirements(
    latest_state: WorkflowExecutionState,
    repair_steps: tuple[str, ...],
    force_steps: tuple[str, ...],
) -> None:
    """Ensure repair requirements are satisfied when needed."""
    if latest_state.repair_required and not (repair_steps or force_steps):
        raise RuntimeError(
            latest_state.repair_hint
            or "Workflow resume requires explicit --repair-steps or --force-steps"
        )


def load_resume_manifest(
    *,
    manifest_service: _WorkflowManifestService,
    latest_state: WorkflowExecutionState,
) -> WorkflowManifest:
    """Load the manifest referenced by one persisted execution state."""
    manifest = manifest_service.manifest_port.get(latest_state.manifest_id)
    if manifest is None:
        raise RuntimeError(
            "Workflow resume failed because the persisted manifest could not be loaded"
        )
    return manifest


def normalize_resume_state(
    latest_state: WorkflowExecutionState,
    *,
    workflow_state_port: WorkflowExecutionStatePort,
    now_factory: Callable[[], datetime],
) -> WorkflowExecutionState:
    """Downgrade stale running state into an incomplete resumable snapshot."""
    if latest_state.status != "running":
        return latest_state
    normalized_state = replace(
        latest_state,
        status="incomplete",
        updated_at=now_factory(),
    )
    workflow_state_port.save(normalized_state)
    return normalized_state


def resolve_skipped_step_ids(
    *,
    state: WorkflowExecutionState,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> frozenset[str]:
    """Preserve only successful steps that are not being forced or repaired."""
    forced_or_repaired = {*force_steps, *repair_steps}
    return frozenset(
        step.step_id
        for step in state.steps
        if step.status == "success" and step.step_id not in forced_or_repaired
    )


def resolve_completed_transform_fingerprints(
    *,
    state: WorkflowExecutionState,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> dict[str, str]:
    """Filter committed transform fingerprints through force/repair selectors."""
    forced_or_repaired = {*force_steps, *repair_steps}
    return {
        step_id: fingerprint
        for step_id, fingerprint in state.completed_transform_fingerprints.items()
        if step_id not in forced_or_repaired
    }
