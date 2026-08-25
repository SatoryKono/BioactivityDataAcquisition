"""Workflow execution recording context model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.ports import WorkflowExecutionStatePort

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow.ledger_service import (
        WorkflowLedgerService,
    )


@dataclass(slots=True)
class WorkflowExecutionRecorder:
    """Mutable recording context for one locked workflow execution."""

    ledger: WorkflowLedgerService
    state_port: WorkflowExecutionStatePort
    state: WorkflowExecutionState


__all__ = ["WorkflowExecutionRecorder"]
