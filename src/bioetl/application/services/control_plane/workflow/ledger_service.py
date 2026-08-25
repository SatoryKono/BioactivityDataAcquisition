"""Application service for append-only workflow-ledger events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from bioetl.application.services.control_plane.ledger.idempotency import (
    build_control_plane_idempotency_key,
)
from bioetl.domain.control_plane import WorkflowLedgerEntry, WorkflowManifest
from bioetl.domain.control_plane.workflow_ledger import (
    STEP_COMMIT_PENDING_CONFIRMATION_EVENT,
    STEP_COMPLETED_EVENT,
    STEP_STARTED_EVENT,
    WORKFLOW_FAILED_EVENT,
    WORKFLOW_FINISHED_EVENT,
    WORKFLOW_FORCE_REQUESTED_EVENT,
    WORKFLOW_MANIFEST_CREATED_EVENT,
    WORKFLOW_REPAIR_REQUESTED_EVENT,
    WORKFLOW_RESUMED_EVENT,
    WORKFLOW_STARTED_EVENT,
)
from bioetl.domain.ports import WorkflowLedgerPort
from bioetl.domain.types import RunID

__all__ = ["WorkflowLedgerService"]

_IDEMPOTENCY_KEY_FIELDS = (
    "manifest_id",
    "workflow_run_id",
    "event_type",
    "event_family",
    "status",
    "step_id",
    "step_kind",
    "message",
    "error_type",
    "details",
)


def _missing_entry_id_factory() -> str:
    raise RuntimeError(
        "workflow ledger entry_id_factory must be supplied by composition root"
    )


def _missing_occurred_at_factory() -> datetime:
    raise RuntimeError(
        "workflow ledger occurred_at_factory must be supplied by composition root"
    )


def _build_workflow_ledger_idempotency_key(payload: Mapping[str, object]) -> str:
    return build_control_plane_idempotency_key(
        payload,
        fields=_IDEMPOTENCY_KEY_FIELDS,
    )


@dataclass(slots=True)
class WorkflowLedgerService:
    """Append immutable lifecycle entries for one workflow manifest."""

    ledger_port: WorkflowLedgerPort
    manifest_id: str
    workflow_run_id: RunID
    workflow_name: str
    _entry_id_factory: Callable[[], str] = field(
        default_factory=lambda: _missing_entry_id_factory
    )
    _occurred_at_factory: Callable[[], datetime] = field(
        default_factory=lambda: _missing_occurred_at_factory
    )

    def record_manifest_created(
        self, manifest: WorkflowManifest
    ) -> WorkflowLedgerEntry:
        """Record workflow-manifest creation as the first control-plane event."""
        return self._append(
            event_type=WORKFLOW_MANIFEST_CREATED_EVENT,
            status="created",
            details={
                "execution_fingerprint": manifest.execution_fingerprint,
                "workflow_name": manifest.workflow_name,
                "workflow_version": manifest.workflow_version,
            },
        )

    def record_workflow_started(self, *, resumed: bool = False) -> WorkflowLedgerEntry:
        """Record the transition into active workflow execution."""
        return self._append(
            event_type=(WORKFLOW_RESUMED_EVENT if resumed else WORKFLOW_STARTED_EVENT),
            status="running",
        )

    def record_step_started(
        self,
        *,
        step_id: str,
        step_kind: str,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        """Record step execution start."""
        return self._append(
            event_type=STEP_STARTED_EVENT,
            status="running",
            step_id=step_id,
            step_kind=step_kind,
            details=details,
        )

    def record_step_completed(
        self,
        *,
        step_id: str,
        step_kind: str,
        status: str,
        message: str | None = None,
        error_type: str | None = None,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        """Record workflow step completion outcome."""
        return self._append(
            event_type=STEP_COMPLETED_EVENT,
            status=status,
            step_id=step_id,
            step_kind=step_kind,
            message=message,
            error_type=error_type,
            details=details,
        )

    def record_step_commit_pending_confirmation(
        self,
        *,
        step_id: str,
        step_kind: str,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        """Record a destructive mutation that committed before terminal confirmation."""
        return self._append(
            event_type=STEP_COMMIT_PENDING_CONFIRMATION_EVENT,
            status="commit_pending_confirmation",
            step_id=step_id,
            step_kind=step_kind,
            details=details,
        )

    def record_workflow_finished(
        self,
        *,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        """Record successful workflow completion."""
        return self._append(
            event_type=WORKFLOW_FINISHED_EVENT,
            status="success",
            details=details,
        )

    def record_workflow_failed(
        self,
        *,
        message: str,
        error_type: str | None,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        """Record failed workflow completion."""
        return self._append(
            event_type=WORKFLOW_FAILED_EVENT,
            status="failed",
            message=message,
            error_type=error_type,
            details=details,
        )

    def record_repair_requested(
        self,
        *,
        step_ids: tuple[str, ...],
    ) -> WorkflowLedgerEntry:
        """Record explicit operator repair intent."""
        return self._append(
            event_type=WORKFLOW_REPAIR_REQUESTED_EVENT,
            status="requested",
            details={"step_ids": list(step_ids)},
        )

    def record_force_requested(
        self,
        *,
        step_ids: tuple[str, ...],
    ) -> WorkflowLedgerEntry:
        """Record explicit operator force intent."""
        return self._append(
            event_type=WORKFLOW_FORCE_REQUESTED_EVENT,
            status="requested",
            details={"step_ids": list(step_ids)},
        )

    def _append(
        self,
        *,
        event_type: str,
        status: str | None = None,
        step_id: str | None = None,
        step_kind: str | None = None,
        message: str | None = None,
        error_type: str | None = None,
        details: dict[str, object] | None = None,
    ) -> WorkflowLedgerEntry:
        entry = WorkflowLedgerEntry(
            entry_id=self._entry_id_factory(),
            manifest_id=self.manifest_id,
            workflow_run_id=self.workflow_run_id,
            event_type=event_type,
            occurred_at=self._occurred_at_factory(),
            status=status,
            step_id=step_id,
            step_kind=step_kind,
            message=message,
            error_type=error_type,
            details=details,
        )
        payload = entry.to_dict()
        payload["idempotency_key"] = _build_workflow_ledger_idempotency_key(payload)
        persisted_entry = WorkflowLedgerEntry.from_dict(payload)
        self.ledger_port.append(persisted_entry)
        return persisted_entry
