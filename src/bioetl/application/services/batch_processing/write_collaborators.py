"""Optional runtime collaborators for batch record processing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class RecordProcessorWriteCollaborators:
    """Optional collaborators for write-stage quarantine handling."""

    quarantine_manager: QuarantineRuntimeService | None = None
    domain_event_emitter: DomainEventEmitterProtocol | None = None


WriteLayerStatus = Literal["written", "quarantined", "blocked", "skipped"]


@dataclass(frozen=True, slots=True)
class LayerWriteOutcome:
    """Typed result of one storage-layer write attempt."""

    layer: str
    status: WriteLayerStatus
    candidate_count: int
    confirmed_count: int = 0
    quarantined_count: int = 0
    write_result: object | None = None


@dataclass(frozen=True, slots=True)
class LayerWriteContext:
    """Collaborators shared by Silver and Gold write attempts."""

    execute_with_span: Callable[..., Awaitable[object]]
    writer: BatchWriter
    quarantine_manager: QuarantineRuntimeService
    logger: LoggerPort
    run_id: RunID | None
    domain_event_emitter: DomainEventEmitterProtocol | None
