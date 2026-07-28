"""Runtime-management bundle for composite runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        CompositeCheckpointService,
        FSMStateHelperService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import QuarantinePort

@dataclass(slots=True)
class RuntimeManagementServicesBundle:
    """Checkpoint, FSM, DQ, and quarantine services for runtime orchestration."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None

__all__ = ["RuntimeManagementServicesBundle"]
