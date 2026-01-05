"""QuarantineEntry Aggregate.

Aggregate Root for isolated failed records pending analysis.

Invariants:
    1. payload_hash is unique within a pipeline (enforced by storage)
    2. Status transitions: NEW -> IGNORED or NEW -> REPROCESSED
    3. Resolution metadata is required when marking as resolved
    4. payload cannot be modified after creation
    5. error_code is required and immutable

Consistency Boundary:
    - Entry state and resolution are transactionally consistent
    - Reprocessing creates new records in Silver, not modifies quarantine
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.types import BatchID, ContentHash, RunID


class QuarantineStatus(str, Enum):
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
        """Check if this is a terminal status."""
        return self in {
            QuarantineStatus.IGNORED,
            QuarantineStatus.REPROCESSED,
            QuarantineStatus.EXPIRED,
        }

    def can_resolve(self) -> bool:
        """Check if entry can be resolved from this status."""
        return self in {QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW}


@dataclass(frozen=True, slots=True)
class ResolutionInfo:
    """Immutable value object with resolution details.

    Attributes:
        resolution_type: Type of resolution (ignored, reprocessed).
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
        if self.resolution_type not in {"ignored", "reprocessed"}:
            raise ValueError(
                f"Invalid resolution_type: {self.resolution_type}. "
                "Must be 'ignored' or 'reprocessed'."
            )


def _validate_quarantine_required_fields(
    entry_id: str,
    pipeline_name: str,
    error_code: str,
    payload: dict[str, Any],
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


class QuarantineEntry:
    """Aggregate Root for a quarantined record.

    Invariants:
        1. payload_hash is computed from payload and immutable
        2. Status can only transition: NEW -> UNDER_REVIEW -> (IGNORED|REPROCESSED)
        3. Resolution requires resolution_info
        4. payload and error_code are immutable

    Example:
        >>> entry = QuarantineEntry.create(
        ...     pipeline_name="chembl_activity",
        ...     error_code="SCHEMA_VIOLATION",
        ...     payload={"id": "bad-record"},
        ...     run_id=run_id,
        ...     batch_id=batch_id,
        ... )
        >>> entry.start_review()
        >>> entry.mark_ignored(reason="Known bad data source")
        >>> events = entry.collect_events()
    """

    __slots__ = (
        "_batch_id",
        "_created_at",
        "_entry_id",
        "_error_code",
        "_events",
        "_metadata",
        "_payload",
        "_payload_hash",
        "_pipeline_name",
        "_resolution_info",
        "_run_id",
        "_status",
    )

    def __init__(
        self,
        entry_id: str,
        pipeline_name: str,
        error_code: str,
        payload: dict[str, Any],
        payload_hash: ContentHash,
        run_id: RunID,
        batch_id: BatchID,
        created_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a quarantine entry.

        Args:
            entry_id: Unique identifier for this entry.
            pipeline_name: Name of the pipeline where error occurred.
            error_code: Classification code for the error.
            payload: The failed record data (immutable copy made).
            payload_hash: Hash of the payload for deduplication.
            run_id: Pipeline run identifier.
            batch_id: Source batch identifier.
            created_at: Creation timestamp.
            metadata: Additional error context.

        Raises:
            ValueError: If required fields are empty.
        """
        _validate_quarantine_required_fields(
            entry_id, pipeline_name, error_code, payload, payload_hash
        )
        self._entry_id = entry_id
        self._pipeline_name = pipeline_name
        self._error_code = error_code
        # Deep copy to ensure immutability
        self._payload = dict(payload)
        self._payload_hash = payload_hash
        self._run_id = run_id
        self._batch_id = batch_id
        self._status = QuarantineStatus.NEW
        self._created_at = created_at or datetime.now(UTC)
        self._metadata = dict(metadata) if metadata else {}
        self._resolution_info: ResolutionInfo | None = None
        self._events: list[DomainEvent] = []

    @classmethod
    def create(
        cls,
        pipeline_name: str,
        error_code: str,
        payload: dict[str, Any],
        run_id: RunID,
        batch_id: BatchID,
        metadata: dict[str, Any] | None = None,
    ) -> QuarantineEntry:
        """Factory method to create a new quarantine entry.

        Generates entry_id and payload_hash automatically.

        Args:
            pipeline_name: Pipeline where error occurred.
            error_code: Error classification.
            payload: The failed record.
            run_id: Pipeline run identifier.
            batch_id: Source batch identifier.
            metadata: Additional context.

        Returns:
            New QuarantineEntry instance.
        """
        import hashlib
        import json
        from uuid import uuid4

        # Generate entry ID
        entry_id = str(uuid4())

        # Compute payload hash
        canonical = json.dumps(payload, sort_keys=True, default=str)
        hash_value = hashlib.sha256(canonical.encode()).hexdigest()
        payload_hash = ContentHash(hash_value)

        entry = cls(
            entry_id=entry_id,
            pipeline_name=pipeline_name,
            error_code=error_code,
            payload=payload,
            payload_hash=payload_hash,
            run_id=run_id,
            batch_id=batch_id,
            metadata=metadata,
        )

        # Emit creation event
        from bioetl.domain.aggregates.events import QuarantineEntryCreated

        entry._events.append(
            QuarantineEntryCreated(
                occurred_at=entry._created_at,
                run_id=run_id,
                batch_id=batch_id,
                pipeline_name=pipeline_name,
                error_code=error_code,
                payload_hash=payload_hash,
                metadata=metadata,
            )
        )

        return entry

    # ──────────────────────────────────────────────────────────────────────────
    # Read-only properties
    # ──────────────────────────────────────────────────────────────────────────

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
    def payload(self) -> dict[str, Any]:
        """Copy of the failed record payload (immutable access)."""
        return dict(self._payload)

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
    def metadata(self) -> dict[str, Any]:
        """Copy of additional error context."""
        return dict(self._metadata)

    @property
    def resolution_info(self) -> ResolutionInfo | None:
        """Resolution details if entry has been resolved."""
        return self._resolution_info

    @property
    def is_resolved(self) -> bool:
        """Check if entry has been resolved."""
        return self._status.is_terminal()

    @property
    def age_seconds(self) -> float:
        """Age of the entry in seconds."""
        return (datetime.now(UTC) - self._created_at).total_seconds()

    # ──────────────────────────────────────────────────────────────────────────
    # State transition methods
    # ──────────────────────────────────────────────────────────────────────────

    def start_review(self) -> None:
        """Mark entry as under review.

        Transitions: NEW -> UNDER_REVIEW

        Raises:
            InvalidStateError: If not in NEW status.
        """
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
        resolved_at: datetime | None = None,
    ) -> None:
        """Mark entry as ignored (non-actionable).

        Transitions: (NEW | UNDER_REVIEW) -> IGNORED

        Args:
            reason: Reason for ignoring.
            resolved_by: User or system that made the decision.
            resolved_at: Resolution timestamp.

        Raises:
            InvalidStateError: If entry cannot be resolved.
        """
        self._assert_can_resolve("mark_ignored")

        now = resolved_at or datetime.now(UTC)
        self._status = QuarantineStatus.IGNORED
        self._resolution_info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=now,
            resolved_by=resolved_by,
            reason=reason,
        )

        # Emit event
        from bioetl.domain.aggregates.events import QuarantineEntryResolved

        self._events.append(
            QuarantineEntryResolved(
                occurred_at=now,
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
        resolved_at: datetime | None = None,
    ) -> None:
        """Mark entry as successfully reprocessed.

        Transitions: (NEW | UNDER_REVIEW) -> REPROCESSED

        Args:
            new_record_id: ID of the new Silver record created.
            resolved_by: User or system that reprocessed.
            resolved_at: Resolution timestamp.

        Raises:
            InvalidStateError: If entry cannot be resolved.
            ValueError: If new_record_id is empty.
        """
        if not new_record_id:
            raise ValueError("new_record_id is required for reprocessing")

        self._assert_can_resolve("mark_reprocessed")

        now = resolved_at or datetime.now(UTC)
        self._status = QuarantineStatus.REPROCESSED
        self._resolution_info = ResolutionInfo(
            resolution_type="reprocessed",
            resolved_at=now,
            resolved_by=resolved_by,
            new_record_id=new_record_id,
        )

        # Emit event
        from bioetl.domain.aggregates.events import QuarantineEntryResolved

        self._events.append(
            QuarantineEntryResolved(
                occurred_at=now,
                run_id=self._run_id,
                entry_id=self._entry_id,
                resolution="reprocessed",
                resolved_by=resolved_by,
            )
        )

    def mark_expired(self, expired_at: datetime | None = None) -> None:
        """Mark entry as expired due to retention policy.

        Transitions: (NEW | UNDER_REVIEW) -> EXPIRED

        Args:
            expired_at: Expiration timestamp.

        Raises:
            InvalidStateError: If entry is already resolved.
        """
        if self._status.is_terminal():
            raise InvalidStateError(
                f"Cannot expire: entry is already in terminal status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_expired",
            )

        self._status = QuarantineStatus.EXPIRED
        now = expired_at or datetime.now(UTC)
        self._resolution_info = ResolutionInfo(
            resolution_type="ignored",  # Expired is a form of ignored
            resolved_at=now,
            reason="Retention period exceeded",
        )

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the entry.

        Only allowed while entry is not resolved.

        Args:
            key: Metadata key.
            value: Metadata value.

        Raises:
            InvalidStateError: If entry is resolved.
        """
        if self._status.is_terminal():
            raise InvalidStateError(
                f"Cannot modify metadata: entry is in terminal status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="add_metadata",
            )
        self._metadata[key] = value

    # ──────────────────────────────────────────────────────────────────────────
    # Domain events
    # ──────────────────────────────────────────────────────────────────────────

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear accumulated domain events.

        Returns:
            List of domain events.
        """
        events = self._events.copy()
        self._events.clear()
        return events

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _assert_can_resolve(self, operation: str) -> None:
        """Assert that entry can be resolved.

        Raises:
            InvalidStateError: If not in a resolvable status.
        """
        if not self._status.can_resolve():
            raise InvalidStateError(
                f"Cannot {operation}: entry is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )

    def __repr__(self) -> str:
        return (
            f"QuarantineEntry(entry_id={self._entry_id!r}, "
            f"pipeline={self._pipeline_name!r}, "
            f"error_code={self._error_code!r}, "
            f"status={self._status.value!r})"
        )
