"""Application-level protocol for publishing typed domain events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent

__all__ = ["DomainEventEmitterProtocol"]


class DomainEventEmitterProtocol(Protocol):
    """Minimal runtime contract for typed domain-event publication."""

    def emit_domain_event(self, event: DomainEvent) -> None:
        """Publish one typed domain event to the canonical observability path."""
