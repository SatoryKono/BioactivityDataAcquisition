"""Quarantine value objects and helpers.

Contains QuarantineStatus enum, ResolutionInfo frozen dataclass,
and validation helper used by QuarantineEntry aggregate.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import BronzeRecord, ContentHash

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, MetaDict, RunID

__all__ = [
    "QuarantineStatus",
    "ResolutionInfo",
]


class QuarantineStatus(StrEnum):
    """Status of a quarantine entry."""

    NEW = "new"
    """Newly quarantined, needs triage."""

    UNDER_REVIEW = "under_review"
    """Currently being analyzed."""

    IGNORED = "ignored"
    """Reviewed and marked as non-actionable."""

    REPROCESSED = "reprocessed"
    """Successfully reprocessed and moved to Silver."""

    EXPIRED = "expired"
    """Entry exceeded retention period."""

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

    _entry_id: str = cast(Any, None)
    _pipeline_name: str = cast(Any, None)
    _error_code: str = cast(Any, None)
    _payload: BronzeRecord = cast(Any, None)
    _payload_hash: ContentHash = cast(Any, None)
    _run_id: RunID = cast(Any, None)
    _batch_id: BatchID = cast(Any, None)
    _status: QuarantineStatus = cast(Any, None)
    _created_at: datetime = cast(Any, None)
    _metadata: MetaDict = cast(Any, None)
    _resolution_info: ResolutionInfo | None = cast(Any, None)

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
