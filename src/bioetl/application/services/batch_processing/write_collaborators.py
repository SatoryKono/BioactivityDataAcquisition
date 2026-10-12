"""Optional runtime collaborators for batch record processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )


@dataclass(frozen=True, slots=True)
class RecordProcessorWriteCollaborators:
    """Optional collaborators for write-stage quarantine handling."""

    quarantine_manager: QuarantineRuntimeService | None = None
    domain_event_emitter: DomainEventEmitterProtocol | None = None
