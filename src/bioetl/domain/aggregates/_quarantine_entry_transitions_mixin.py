# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""State transition and event helpers for `QuarantineEntry` aggregate."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import MetaDict, RunID


class QuarantineEntryTransitionsMixin:
    """Host mixin implementing state machine and event collection."""

    _entry_id: str
    _run_id: RunID
    _status: QuarantineStatus
    _resolution_info: ResolutionInfo | None
    _metadata: MetaDict
    _events: list[DomainEvent]

    def start_review(self) -> None:
        """Mark entry as under review."""
        if self._status != QuarantineStatus.NEW:
            raise InvalidStateError(
                f"Cannot start review: entry is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="start_review",
            )
        self._status = QuarantineStatus.UNDER_REVIEW

    def mark_ignored(
        self,
        reason: str | None = None,
        resolved_by: str | None = None,
        *,
        resolved_at: datetime,
    ) -> None:
        """Mark entry as ignored (non-actionable).

        Args:
            reason: Optional human-readable explanation for ignoring the entry.
            resolved_by: Optional identifier of the user or system that resolved it.
            resolved_at: Explicit resolution timestamp.
        """
        self._assert_can_resolve("mark_ignored")

        self._status = QuarantineStatus.IGNORED
        self._resolution_info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=resolved_at,
            resolved_by=resolved_by,
            reason=reason,
        )

        from bioetl.domain.aggregates.events import QuarantineEntryResolved

        self._events.append(
            QuarantineEntryResolved(
                occurred_at=resolved_at,
                run_id=self._run_id,
                entry_id=self._entry_id,
                resolution="ignored",
                resolved_by=resolved_by,
            )
        )

    def mark_reprocessed(
        self,
        new_record_id: str,
        resolved_by: str | None = None,
        *,
        resolved_at: datetime,
    ) -> None:
        """Mark entry as successfully reprocessed.

        Args:
            new_record_id: Identifier of the replacement record created after reprocessing.
            resolved_by: Optional identifier of the user or system that reprocessed it.
            resolved_at: Explicit resolution timestamp.
        """
        if not new_record_id:
            raise ValueError("new_record_id is required for reprocessing")

        self._assert_can_resolve("mark_reprocessed")

        self._status = QuarantineStatus.REPROCESSED
        self._resolution_info = ResolutionInfo(
            resolution_type="reprocessed",
            resolved_at=resolved_at,
            resolved_by=resolved_by,
            new_record_id=new_record_id,
        )

        from bioetl.domain.aggregates.events import QuarantineEntryResolved

        self._events.append(
            QuarantineEntryResolved(
                occurred_at=resolved_at,
                run_id=self._run_id,
                entry_id=self._entry_id,
                resolution="reprocessed",
                resolved_by=resolved_by,
            )
        )

    def mark_expired(self, *, expired_at: datetime) -> None:
        """Mark entry as expired due to retention policy.

        Args:
            expired_at: Explicit expiry timestamp.
        """
        if self._status.is_terminal():
            raise InvalidStateError(
                f"Cannot expire: entry is already in terminal status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_expired",
            )

        self._status = QuarantineStatus.EXPIRED
        self._resolution_info = ResolutionInfo(
            resolution_type="expired",
            resolved_at=expired_at,
            reason="Retention period exceeded",
        )

    def add_metadata(self, key: str, value: object) -> None:
        """Add metadata to the entry while entry is unresolved.

        Args:
            key: Metadata key to add or update.
            value: Metadata value to associate with the key.
        """
        if self._status.is_terminal():
            raise InvalidStateError(
                f"Cannot modify metadata: entry is in terminal status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="add_metadata",
            )
        self._metadata[key] = value

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear accumulated domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def _assert_can_resolve(self, operation: str) -> None:
        """Assert that entry can be resolved."""
        if not self._status.can_resolve():
            raise InvalidStateError(
                f"Cannot {operation}: entry is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


__all__ = ["QuarantineEntryTransitionsMixin"]
