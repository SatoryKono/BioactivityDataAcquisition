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
        return {
            "step_id": self.step_id,
            "step_kind": self.step_kind,
            "status": self.status,
            "fingerprint": self.fingerprint,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "destructive": self.destructive,
            "commit_pending_confirmation": self.commit_pending_confirmation,
            "mutation_details": self.mutation_details,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowStepState:
        """Hydrate one workflow step-state snapshot."""
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
            mutation_details=(
                {str(key): value for key, value in mutation_details.items()}
                if isinstance(
                    (mutation_details := payload.get("mutation_details")), dict
                )
                else None
            ),
        )


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
        return {
            "workflow_run_id": str(self.workflow_run_id),
            "manifest_id": self.manifest_id,
            "workflow_name": self.workflow_name,
            "execution_fingerprint": self.execution_fingerprint,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": (
                None if self.completed_at is None else self.completed_at.isoformat()
            ),
            "selected_step_ids": list(self.selected_step_ids),
            "steps": [step.to_dict() for step in self.steps],
            "completed_transform_fingerprints": dict(
                self.completed_transform_fingerprints
            ),
            "last_event_id": self.last_event_id,
            "last_error_type": self.last_error_type,
            "last_error_message": self.last_error_message,
            "repair_required": self.repair_required,
            "repair_hint": self.repair_hint,
            "ambiguous_step_ids": list(self.ambiguous_step_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowExecutionState:
        """Hydrate workflow execution-state from serialized payload."""
        completed_at = payload.get("completed_at")
        fingerprints = payload.get("completed_transform_fingerprints")
        return cls(
            workflow_run_id=RunID(UUID(str(payload["workflow_run_id"]))),
            manifest_id=str(payload["manifest_id"]),
            workflow_name=str(payload["workflow_name"]),
            execution_fingerprint=str(payload["execution_fingerprint"]),
            status=str(payload["status"]),
            started_at=datetime.fromisoformat(str(payload["started_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            completed_at=(
                None
                if completed_at is None
                else datetime.fromisoformat(str(completed_at))
            ),
            selected_step_ids=tuple(
                str(item) for item in _load_list(payload.get("selected_step_ids"))
            ),
            steps=tuple(
                WorkflowStepState.from_dict(item)
                for item in _load_list_of_dicts(payload.get("steps"))
            ),
            completed_transform_fingerprints=(
                {str(key): str(value) for key, value in fingerprints.items()}
                if isinstance(fingerprints, dict)
                else {}
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
