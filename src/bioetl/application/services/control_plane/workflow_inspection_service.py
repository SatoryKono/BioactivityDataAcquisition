"""Workflow inspection service aligned with control-plane taxonomy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from bioetl.domain.control_plane import (
    WorkflowExecutionState,
    WorkflowManifest,
)
from bioetl.domain.ports import (
    WorkflowExecutionStatePort,
    WorkflowLedgerPort,
    WorkflowManifestPort,
)
from bioetl.domain.types import RunID

__all__ = ["WorkflowInspectionResult", "WorkflowInspectionService"]


@dataclass(frozen=True, slots=True)
class WorkflowInspectionResult:
    """Operator-facing workflow inspection payload."""

    workflow_name: str
    workflow_run_id: str
    manifest_id: str
    execution_fingerprint: str
    status: str
    workflow_version: str
    selected_step_ids: tuple[str, ...]
    step_states: tuple[dict[str, object], ...]
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    last_error_type: str | None
    last_error_message: str | None
    repair_required: bool
    repair_hint: str | None
    ambiguous_step_ids: tuple[str, ...]
    ledger_entry_count: int


@dataclass(slots=True)
class WorkflowInspectionService:
    """Resolve workflow status from manifest, ledger, and execution state."""

    manifest_port: WorkflowManifestPort
    ledger_port: WorkflowLedgerPort
    state_port: WorkflowExecutionStatePort

    def inspect_latest(self, workflow_name: str) -> WorkflowInspectionResult | None:
        """Return the latest workflow execution state for a workflow name."""
        state = self.state_port.get_latest(workflow_name)
        if state is None:
            return None
        return self._build_result(state)

    def inspect_run_id(self, workflow_run_id: str) -> WorkflowInspectionResult | None:
        """Return workflow inspection payload for one workflow run identifier."""
        state = self.state_port.get_by_run_id(RunID(UUID(workflow_run_id)))
        if state is None:
            return None
        return self._build_result(state)

    def _build_result(
        self,
        state: WorkflowExecutionState,
    ) -> WorkflowInspectionResult:
        manifest = self.manifest_port.get(state.manifest_id)
        if manifest is None:
            raise RuntimeError(
                "Workflow inspection failed because the persisted manifest could not be loaded"
            )
        return WorkflowInspectionResult(
            workflow_name=state.workflow_name,
            workflow_run_id=str(state.workflow_run_id),
            manifest_id=state.manifest_id,
            execution_fingerprint=state.execution_fingerprint,
            status=state.status,
            workflow_version=manifest.workflow_version,
            selected_step_ids=state.selected_step_ids,
            step_states=tuple(step.to_dict() for step in state.steps),
            started_at=state.started_at,
            updated_at=state.updated_at,
            completed_at=state.completed_at,
            last_error_type=state.last_error_type,
            last_error_message=state.last_error_message,
            repair_required=state.repair_required,
            repair_hint=state.repair_hint,
            ambiguous_step_ids=state.ambiguous_step_ids,
            ledger_entry_count=len(self.ledger_port.list_entries(state.manifest_id)),
        )
