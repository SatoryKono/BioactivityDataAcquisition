"""Quarantine value objects and helpers.

Contains QuarantineStatus enum, ResolutionInfo frozen dataclass,
and validation helper used by QuarantineEntry aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from bioetl.domain.types import BronzeRecord, ContentHash

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
        allowed = {
            status.value
            for status in QuarantineStatus
            if status.is_terminal()
        }
        if self.resolution_type not in allowed:
            allowed_list = ", ".join(repr(value) for value in sorted(allowed))
            raise ValueError(
                f"Invalid resolution_type: {self.resolution_type}. "
                f"Must be one of: {allowed_list}."
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
