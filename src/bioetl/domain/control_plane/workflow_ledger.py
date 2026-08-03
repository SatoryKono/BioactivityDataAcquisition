"""Workflow control-plane ledger models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from bioetl.domain.types import RunID

__all__ = [
    "STEP_COMMIT_PENDING_CONFIRMATION_EVENT",
    "STEP_COMPLETED_EVENT",
    "STEP_STARTED_EVENT",
    "WORKFLOW_FAILED_EVENT",
    "WORKFLOW_FINISHED_EVENT",
    "WORKFLOW_FORCE_REQUESTED_EVENT",
    "WORKFLOW_LEDGER_EVENT_TYPES",
    "WORKFLOW_MANIFEST_CREATED_EVENT",
    "WORKFLOW_REPAIR_REQUESTED_EVENT",
    "WORKFLOW_RESUMED_EVENT",
    "WORKFLOW_STARTED_EVENT",
    "WorkflowLedgerEntry",
    "infer_workflow_ledger_event_family",
]

WORKFLOW_MANIFEST_CREATED_EVENT = "workflow_manifest_created"
WORKFLOW_STARTED_EVENT = "workflow_started"
WORKFLOW_RESUMED_EVENT = "workflow_resumed"
WORKFLOW_FINISHED_EVENT = "workflow_finished"
WORKFLOW_FAILED_EVENT = "workflow_failed"
STEP_STARTED_EVENT = "workflow_step_started"
STEP_COMPLETED_EVENT = "workflow_step_completed"
STEP_COMMIT_PENDING_CONFIRMATION_EVENT = "workflow_step_commit_pending_confirmation"
WORKFLOW_REPAIR_REQUESTED_EVENT = "workflow_repair_requested"
WORKFLOW_FORCE_REQUESTED_EVENT = "workflow_force_requested"

WORKFLOW_LEDGER_EVENT_TYPES: tuple[str, ...] = (
    WORKFLOW_MANIFEST_CREATED_EVENT,
    WORKFLOW_STARTED_EVENT,
    WORKFLOW_RESUMED_EVENT,
    WORKFLOW_FINISHED_EVENT,
    WORKFLOW_FAILED_EVENT,
    STEP_STARTED_EVENT,
    STEP_COMPLETED_EVENT,
    STEP_COMMIT_PENDING_CONFIRMATION_EVENT,
    WORKFLOW_REPAIR_REQUESTED_EVENT,
    WORKFLOW_FORCE_REQUESTED_EVENT,
)


def infer_workflow_ledger_event_family(event_type: str) -> str:
    """Return the canonical workflow-ledger event family label."""
    if event_type in {
        STEP_STARTED_EVENT,
        STEP_COMPLETED_EVENT,
        STEP_COMMIT_PENDING_CONFIRMATION_EVENT,
    }:
        return "step"
    if event_type in {
        WORKFLOW_REPAIR_REQUESTED_EVENT,
        WORKFLOW_FORCE_REQUESTED_EVENT,
    }:
        return "operator"
    return "workflow"


@dataclass(frozen=True, slots=True)
class WorkflowLedgerEntry:
    """Append-only control-plane event for one workflow execution."""

    entry_id: str
    manifest_id: str
    workflow_run_id: RunID
    event_type: str
    occurred_at: datetime
    event_family: str | None = None
    status: str | None = None
    step_id: str | None = None
    step_kind: str | None = None
    message: str | None = None
    error_type: str | None = None
    idempotency_key: str | None = None
    details: dict[str, object] | None = None

    def __post_init__(self) -> None:
        normalized_event_type = str(self.event_type).strip().lower()
        object.__setattr__(self, "event_type", normalized_event_type)
        if self.event_family is None:
            object.__setattr__(
                self,
                "event_family",
                infer_workflow_ledger_event_family(normalized_event_type),
            )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable ledger entry payload."""
        payload = asdict(self)
        payload["workflow_run_id"] = str(self.workflow_run_id)
        payload["occurred_at"] = self.occurred_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowLedgerEntry:
        """Hydrate one workflow-ledger entry from serialized payload."""
        details = payload.get("details")
        return cls(
            entry_id=str(payload["entry_id"]),
            manifest_id=str(payload["manifest_id"]),
            workflow_run_id=RunID(UUID(str(payload["workflow_run_id"]))),
            event_type=str(payload["event_type"]),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            event_family=_load_optional_str(payload, "event_family"),
            status=_load_optional_str(payload, "status"),
            step_id=_load_optional_str(payload, "step_id"),
            step_kind=_load_optional_str(payload, "step_kind"),
            message=_load_optional_str(payload, "message"),
            error_type=_load_optional_str(payload, "error_type"),
            idempotency_key=_load_optional_str(payload, "idempotency_key"),
            details=(
                {str(key): value for key, value in details.items()}
                if isinstance(details, dict)
                else None
            ),
        )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)
