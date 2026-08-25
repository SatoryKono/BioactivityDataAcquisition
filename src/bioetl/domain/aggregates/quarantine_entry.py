"""QuarantineEntry public facade and transition behavior."""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates._quarantine_aggregate import QuarantineEntry
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import MetaDict, RunID

__all__ = ["QuarantineEntry", "QuarantineStatus", "ResolutionInfo"]


class QuarantineEntryTransitionsMixin:
    """Host mixin implementing state machine and event collection."""

    _entry_id: str = cast(Any, None)
    _run_id: RunID = cast(Any, None)
    _status: QuarantineStatus = cast(Any, None)
    _resolution_info: ResolutionInfo | None = cast(Any, None)
    _metadata: MetaDict = cast(Any, None)
    _events: list[DomainEvent] = cast(Any, None)

    def start_review(self) -> None:
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
        self._assert_can_resolve("mark_ignored")
        self._status = QuarantineStatus.IGNORED
        self._resolution_info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=resolved_at,
            resolved_by=resolved_by,
            reason=reason,
        )
        self._emit_resolved("ignored", resolved_by, resolved_at)

    def mark_reprocessed(
        self,
        new_record_id: str,
        resolved_by: str | None = None,
        *,
        resolved_at: datetime,
    ) -> None:
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
        self._emit_resolved("reprocessed", resolved_by, resolved_at)

    def _emit_resolved(
        self,
        resolution: str,
        resolved_by: str | None,
        resolved_at: datetime,
    ) -> None:
        from bioetl.domain.aggregates.events import QuarantineEntryResolved

        self._events.append(
            QuarantineEntryResolved(
                occurred_at=resolved_at,
                run_id=self._run_id,
                entry_id=self._entry_id,
                resolution=resolution,
                resolved_by=resolved_by,
            )
        )

    def mark_expired(self, *, expired_at: datetime) -> None:
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
        if self._status.is_terminal():
            raise InvalidStateError(
                f"Cannot modify metadata: entry is in terminal status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="add_metadata",
            )
        self._metadata[key] = value

    def collect_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def _assert_can_resolve(self, operation: str) -> None:
        if not self._status.can_resolve():
            raise InvalidStateError(
                f"Cannot {operation}: entry is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


def __getattr__(name: str) -> object:
    if name == "QuarantineEntry":
        module = importlib.import_module(
            "bioetl.domain.aggregates._quarantine_aggregate"
        )
        return module.QuarantineEntry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
