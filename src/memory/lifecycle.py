"""Explicit lifecycle state machine for persistent memory records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from memory.records import RecordStatus


class IllegalTransitionError(ValueError):
    """Raised when a lifecycle transition violates the memory contract."""


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    """Auditable transition between two record lifecycle states."""

    record_id: str
    previous: RecordStatus
    current: RecordStatus
    reason: str
    actor: str
    occurred_at: str


_LEGAL_TRANSITIONS = {
    RecordStatus.ACTIVE: frozenset(
        {
            RecordStatus.STALE,
            RecordStatus.SUPERSEDED,
            RecordStatus.ARCHIVED,
        }
    ),
    RecordStatus.STALE: frozenset(
        {
            RecordStatus.ACTIVE,
            RecordStatus.SUPERSEDED,
            RecordStatus.ARCHIVED,
        }
    ),
    RecordStatus.SUPERSEDED: frozenset({RecordStatus.ARCHIVED}),
    RecordStatus.ARCHIVED: frozenset(),
}


def can_transition(previous: RecordStatus, current: RecordStatus) -> bool:
    """Return whether the state machine permits a state change."""
    return current in _LEGAL_TRANSITIONS[previous]


def transition(
    *,
    record_id: str,
    previous: RecordStatus,
    current: RecordStatus,
    reason: str,
    actor: str,
    occurred_at: str | None = None,
) -> LifecycleTransition:
    """Validate and create one immutable lifecycle transition."""
    if not reason.strip():
        raise IllegalTransitionError("transition reason must not be empty")
    if not actor.strip():
        raise IllegalTransitionError("transition actor must not be empty")
    if not can_transition(previous, current):
        raise IllegalTransitionError(
            f"illegal memory lifecycle transition: {previous.value} -> {current.value}"
        )
    return LifecycleTransition(
        record_id=record_id,
        previous=previous,
        current=current,
        reason=reason,
        actor=actor,
        occurred_at=occurred_at or datetime.now(UTC).isoformat(),
    )
