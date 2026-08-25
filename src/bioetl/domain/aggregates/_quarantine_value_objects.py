"""Quarantine value objects and helpers.

Contains QuarantineStatus enum, ResolutionInfo frozen dataclass,
and validation helper used by QuarantineEntry aggregate.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BronzeRecord, ContentHash

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import BatchID, MetaDict, RunID

__all__ = [
    "QuarantineEntryTransitionsMixin",
    "QuarantineStatus",
    "ResolutionInfo",
]


class QuarantineStatus(StrEnum):
    """Status of a quarantine entry."""

    NEW = "new"
    UNDER_REVIEW = "under_review"
    IGNORED = "ignored"
    REPROCESSED = "reprocessed"
    EXPIRED = "expired"

    def is_terminal(self) -> bool:
        """Check if this is a terminal status.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {
            QuarantineStatus.IGNORED,
            QuarantineStatus.REPROCESSED,
            QuarantineStatus.EXPIRED,
        }

    def can_resolve(self) -> bool:
        """Check if entry can be resolved from this status.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW}


class QuarantineEntryPropertiesMixin:
    """Host mixin exposing immutable aggregate state and projections."""

    _entry_id: str
    _pipeline_name: str
    _error_code: str
    _payload: BronzeRecord
    _payload_hash: ContentHash
    _run_id: RunID
    _batch_id: BatchID
    _status: QuarantineStatus
    _created_at: datetime
    _metadata: MetaDict
    _resolution_info: ResolutionInfo | None

    @property
    def entry_id(self) -> str:
        return self._entry_id

    @property
    def pipeline_name(self) -> str:
        return self._pipeline_name

    @property
    def error_code(self) -> str:
        return self._error_code

    @property
    def payload(self) -> BronzeRecord:
        return deepcopy(self._payload)

    @property
    def payload_hash(self) -> ContentHash:
        return self._payload_hash

    @property
    def run_id(self) -> RunID:
        return self._run_id

    @property
    def batch_id(self) -> BatchID:
        return self._batch_id

    @property
    def status(self) -> QuarantineStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def metadata(self) -> MetaDict:
        return deepcopy(self._metadata)

    @property
    def resolution_info(self) -> ResolutionInfo | None:
        return self._resolution_info

    @property
    def is_resolved(self) -> bool:
        return self._status.is_terminal()

    @property
    def age_seconds(self) -> float | None:
        if self._resolution_info is None:
            return None
        return (self._resolution_info.resolved_at - self._created_at).total_seconds()

    def age_seconds_at(self, reference_time: datetime) -> float:
        return (reference_time - self._created_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"QuarantineEntry(entry_id={self._entry_id!r}, "
            f"pipeline={self._pipeline_name!r}, error_code={self._error_code!r}, "
            f"status={self._status.value!r})"
        )


def _terminal_resolution_types() -> frozenset[str]:
    return frozenset(
        status.value for status in QuarantineStatus if status.is_terminal()
    )


def _validate_resolution_type(resolution_type: str) -> None:
    allowed = _terminal_resolution_types()
    if resolution_type in allowed:
        return
    allowed_list = ", ".join(repr(value) for value in sorted(allowed))
    raise ValueError(
        f"Invalid resolution_type: {resolution_type}. Must be one of: {allowed_list}."
    )


@dataclass(frozen=True, slots=True)
class ResolutionInfo:
    """Immutable value object with resolution details.

    Attributes:
        resolution_type: Type of resolution (ignored, reprocessed, expired).
        resolved_at: Timestamp of resolution.
        resolved_by: User or system that resolved the entry.
        reason: Reason for the resolution.
        new_record_id: ID of new Silver record if reprocessed.
    """

    resolution_type: str
    resolved_at: datetime
    resolved_by: str | None = None
    reason: str | None = None
    new_record_id: str | None = None

    def __post_init__(self) -> None:
        """Validate resolution info."""
        _validate_resolution_type(self.resolution_type)


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


def _validate_quarantine_required_fields(
    entry_id: str,
    pipeline_name: str,
    error_code: str,
    payload: BronzeRecord,
    payload_hash: ContentHash,
) -> None:
    """Validate required quarantine entry fields (extracted for lower CC)."""
    _required = [
        (entry_id, "entry_id is required"),
        (pipeline_name, "pipeline_name is required"),
        (error_code, "error_code is required"),
        (payload, "payload cannot be empty"),
        (payload_hash, "payload_hash is required"),
    ]
    for field, msg in _required:
        if not field:
            raise ValueError(msg)
