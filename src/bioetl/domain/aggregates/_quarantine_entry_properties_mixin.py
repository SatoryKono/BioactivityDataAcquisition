# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read-only property helpers for `QuarantineEntry` aggregate."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord, ContentHash, MetaDict, RunID


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
        """Unique entry identifier."""
        return self._entry_id

    @property
    def pipeline_name(self) -> str:
        """Pipeline where error occurred."""
        return self._pipeline_name

    @property
    def error_code(self) -> str:
        """Error classification code."""
        return self._error_code

    @property
    def payload(self) -> BronzeRecord:
        """Copy of the failed record payload (immutable access)."""
        return deepcopy(self._payload)

    @property
    def payload_hash(self) -> ContentHash:
        """Hash of the payload for deduplication."""
        return self._payload_hash

    @property
    def run_id(self) -> RunID:
        """Pipeline run identifier."""
        return self._run_id

    @property
    def batch_id(self) -> BatchID:
        """Source batch identifier."""
        return self._batch_id

    @property
    def status(self) -> QuarantineStatus:
        """Current entry status."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """Entry creation timestamp."""
        return self._created_at

    @property
    def metadata(self) -> MetaDict:
        """Copy of additional error context."""
        return deepcopy(self._metadata)

    @property
    def resolution_info(self) -> ResolutionInfo | None:
        """Resolution details if entry has been resolved."""
        return self._resolution_info

    @property
    def is_resolved(self) -> bool:
        """Check if entry has been resolved."""
        return self._status.is_terminal()

    @property
    def age_seconds(self) -> float | None:
        """Resolved lifetime of the entry in seconds, if terminal."""
        if self._resolution_info is None:
            return None
        return (self._resolution_info.resolved_at - self._created_at).total_seconds()

    def age_seconds_at(self, reference_time: datetime) -> float:
        """Return entry age relative to an explicit reference time."""
        return (reference_time - self._created_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"QuarantineEntry(entry_id={self._entry_id!r}, "
            f"pipeline={self._pipeline_name!r}, "
            f"error_code={self._error_code!r}, "
            f"status={self._status.value!r})"
        )


__all__ = ["QuarantineEntryPropertiesMixin"]
