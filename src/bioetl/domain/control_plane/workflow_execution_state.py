"""Workflow execution-state owner models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from bioetl.domain.types import RunID

__all__ = ["WorkflowExecutionState", "WorkflowStepState"]


@dataclass(frozen=True, slots=True)
class WorkflowStepState:
    """Durable execution-state snapshot for one workflow step."""

    step_id: str
    step_kind: str
    status: str
    fingerprint: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    destructive: bool = False
    commit_pending_confirmation: bool = False
    mutation_details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable step-state payload."""
        return _workflow_step_state_to_dict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowStepState:
        """Hydrate one workflow step-state snapshot."""
        return _workflow_step_state_from_dict(cls, payload)


@dataclass(frozen=True, slots=True)
class WorkflowExecutionState:
    """Mutable-owner artifact for workflow resume and operator status."""

    workflow_run_id: RunID
    manifest_id: str
    workflow_name: str
    execution_fingerprint: str
    status: str
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    selected_step_ids: tuple[str, ...]
    steps: tuple[WorkflowStepState, ...]
    completed_transform_fingerprints: dict[str, str]
    last_event_id: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    repair_required: bool = False
    repair_hint: str | None = None
    ambiguous_step_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable execution-state payload."""
        return _workflow_execution_state_to_dict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowExecutionState:
        """Hydrate workflow execution-state from serialized payload."""
        return _workflow_execution_state_from_dict(cls, payload)


def _workflow_step_state_to_dict(step_state: WorkflowStepState) -> dict[str, object]:
    return {
        "step_id": step_state.step_id,
        "step_kind": step_state.step_kind,
        "status": step_state.status,
        "fingerprint": step_state.fingerprint,
        "error_type": step_state.error_type,
        "error_message": step_state.error_message,
        "destructive": step_state.destructive,
        "commit_pending_confirmation": step_state.commit_pending_confirmation,
        "mutation_details": step_state.mutation_details,
    }


def _workflow_step_state_from_dict(
    cls: type[WorkflowStepState],
    payload: dict[str, object],
) -> WorkflowStepState:
    return cls(
        step_id=str(payload["step_id"]),
        step_kind=str(payload["step_kind"]),
        status=str(payload["status"]),
        fingerprint=_load_optional_str(payload, "fingerprint"),
        error_type=_load_optional_str(payload, "error_type"),
        error_message=_load_optional_str(payload, "error_message"),
        destructive=bool(payload.get("destructive", False)),
        commit_pending_confirmation=bool(
            payload.get("commit_pending_confirmation", False)
        ),
        mutation_details=_load_mutation_details(payload.get("mutation_details")),
    )


def _workflow_execution_state_to_dict(
    state: WorkflowExecutionState,
) -> dict[str, object]:
    return {
        "workflow_run_id": str(state.workflow_run_id),
        "manifest_id": state.manifest_id,
        "workflow_name": state.workflow_name,
        "execution_fingerprint": state.execution_fingerprint,
        "status": state.status,
        "started_at": state.started_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "completed_at": _serialize_optional_datetime(state.completed_at),
        "selected_step_ids": list(state.selected_step_ids),
        "steps": [step.to_dict() for step in state.steps],
        "completed_transform_fingerprints": dict(
            state.completed_transform_fingerprints
        ),
        "last_event_id": state.last_event_id,
        "last_error_type": state.last_error_type,
        "last_error_message": state.last_error_message,
        "repair_required": state.repair_required,
        "repair_hint": state.repair_hint,
        "ambiguous_step_ids": list(state.ambiguous_step_ids),
    }


def _workflow_execution_state_from_dict(
    cls: type[WorkflowExecutionState],
    payload: dict[str, object],
) -> WorkflowExecutionState:
    return cls(
        workflow_run_id=RunID(UUID(str(payload["workflow_run_id"]))),
        manifest_id=str(payload["manifest_id"]),
        workflow_name=str(payload["workflow_name"]),
        execution_fingerprint=str(payload["execution_fingerprint"]),
        status=str(payload["status"]),
        started_at=datetime.fromisoformat(str(payload["started_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        completed_at=_deserialize_optional_datetime(payload.get("completed_at")),
        selected_step_ids=tuple(
            str(item) for item in _load_list(payload.get("selected_step_ids"))
        ),
        steps=tuple(
            WorkflowStepState.from_dict(item)
            for item in _load_list_of_dicts(payload.get("steps"))
        ),
        completed_transform_fingerprints=_load_transform_fingerprints(
            payload.get("completed_transform_fingerprints")
        ),
        last_event_id=_load_optional_str(payload, "last_event_id"),
        last_error_type=_load_optional_str(payload, "last_error_type"),
        last_error_message=_load_optional_str(payload, "last_error_message"),
        repair_required=bool(payload.get("repair_required", False)),
        repair_hint=_load_optional_str(payload, "repair_hint"),
        ambiguous_step_ids=tuple(
            str(item) for item in _load_list(payload.get("ambiguous_step_ids"))
        ),
    )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _deserialize_optional_datetime(value: object) -> datetime | None:
    return None if value is None else datetime.fromisoformat(str(value))


def _load_mutation_details(raw_value: object) -> dict[str, object] | None:
    if not isinstance(raw_value, dict):
        return None
    return {str(key): value for key, value in raw_value.items()}


def _load_transform_fingerprints(raw_value: object) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {}
    return {str(key): str(value) for key, value in raw_value.items()}


def _load_list(raw_value: object) -> list[object]:
    if not isinstance(raw_value, list):
        return []
    return list(raw_value)


def _load_list_of_dicts(raw_value: object) -> list[dict[str, object]]:
    return [
        {str(key): value for key, value in item.items()}
        for item in _load_list(raw_value)
        if isinstance(item, dict)
    ]
