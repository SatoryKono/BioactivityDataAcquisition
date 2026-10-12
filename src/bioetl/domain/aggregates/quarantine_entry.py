"""QuarantineEntry Aggregate Root.

Aggregate Root for isolated failed records pending analysis.

Invariants:
    1. payload_hash is unique within a pipeline (enforced by storage)
    2. NEW -> UNDER_REVIEW; NEW or UNDER_REVIEW -> IGNORED|REPROCESSED|EXPIRED
    3. Resolution metadata is required when marking as resolved
    4. payload cannot be modified after creation
    5. error_code is required and immutable

Consistency Boundary:
    - Entry state and resolution are transactionally consistent
    - Reprocessing creates new records in Silver, not modifies quarantine
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineEntryPropertiesMixin,
    QuarantineEntryTransitionsMixin,
    QuarantineStatus,
    ResolutionInfo,
    _validate_quarantine_required_fields,
)
from bioetl.domain.deterministic_identity import deterministic_id
from bioetl.domain.normalization.canonical_json_profile import CanonicalJsonProfile

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.types import BatchID, BronzeRecord, ContentHash, MetaDict, RunID

__all__ = ["QuarantineEntry", "QuarantineStatus", "ResolutionInfo"]


class QuarantineEntry(QuarantineEntryTransitionsMixin, QuarantineEntryPropertiesMixin):
    """Aggregate Root for a quarantined record.

    Invariants:
        1. payload_hash is computed from payload and immutable
        2. NEW -> UNDER_REVIEW; NEW or UNDER_REVIEW -> IGNORED|REPROCESSED|EXPIRED.
        3. Resolution requires resolution_info
        4. payload and error_code are immutable

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import UUID
        >>> from bioetl.domain.types import BatchID, RunID
        >>> run_id = RunID(UUID(int=1))
        >>> batch_id = BatchID(UUID(int=2))
        >>> created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        >>> resolved_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
        >>> entry = QuarantineEntry.create(
        ...     pipeline_name="chembl_activity",
        ...     error_code="SCHEMA_VIOLATION",
        ...     payload={"id": "bad-record"},
        ...     run_id=run_id,
        ...     batch_id=batch_id,
        ...     created_at=created_at,
        ... )
        >>> entry.start_review()
        >>> entry.mark_ignored(reason="Known bad data source", resolved_at=resolved_at)
        >>> events = entry.collect_events()

    Canonical FSM: docs/02-architecture/domain/aggregate-invariants.md.
    Expiry records resolution metadata without an additional domain event.
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
        payload: BronzeRecord,
        payload_hash: ContentHash,
        run_id: RunID,
        batch_id: BatchID,
        *,
        created_at: datetime,
        metadata: MetaDict | None = None,
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
            created_at: Explicit creation timestamp.
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
        # Nested API payloads must not remain aliased to caller-owned objects.
        self._payload = deepcopy(payload)
        self._payload_hash = payload_hash
        self._run_id = run_id
        self._batch_id = batch_id
        self._status = QuarantineStatus.NEW
        self._created_at = created_at
        self._metadata: MetaDict = deepcopy(metadata) if metadata else {}
        self._resolution_info: ResolutionInfo | None = None
        self._events: list[DomainEvent] = []

    @classmethod
    def create(
        cls,
        pipeline_name: str,
        error_code: str,
        payload: BronzeRecord,
        run_id: RunID,
        batch_id: BatchID,
        *,
        created_at: datetime,
        metadata: MetaDict | None = None,
        canonical_profile: CanonicalJsonProfile = CanonicalJsonProfile.DOMAIN_V1,
    ) -> QuarantineEntry:
        """Factory method to create a new quarantine entry.

        Derives entry_id and payload_hash deterministically from explicit inputs.

        Args:
            pipeline_name: Pipeline where error occurred.
            error_code: Error classification.
            payload: The failed record.
            run_id: Pipeline run identifier.
            batch_id: Source batch identifier.
            created_at: Explicit timestamp when the quarantine entry was created.
            metadata: Additional context.
            canonical_profile: Proven byte profile; historical replay must not guess it.

        Returns:
            New QuarantineEntry instance.
        """
        import hashlib

        from bioetl.domain.serialization import serialize_to_json_canonical

        # Compute payload hash
        canonical = serialize_to_json_canonical(payload, profile=canonical_profile)
        hash_value = hashlib.sha256(canonical.encode()).hexdigest()
        payload_hash = ContentHash(hash_value)
        entry_id = deterministic_id(
            "quarantine-entry",
            {
                "batch_id": batch_id,
                "created_at": created_at,
                "error_code": error_code,
                "metadata": metadata or {},
                "payload_hash": payload_hash,
                "pipeline_name": pipeline_name,
                "run_id": run_id,
            },
            profile=canonical_profile,
        )

        entry = cls(
            entry_id=entry_id,
            pipeline_name=pipeline_name,
            error_code=error_code,
            payload=payload,
            payload_hash=payload_hash,
            run_id=run_id,
            batch_id=batch_id,
            created_at=created_at,
            metadata=metadata,
        )

        # Emit creation event
        from bioetl.domain.aggregates.events import QuarantineEntryCreated

        event_metadata = deepcopy(metadata) if metadata is not None else None
        event_id = deterministic_id(
            "QuarantineEntryCreated",
            {
                "occurred_at": entry._created_at,
                "run_id": run_id,
                "batch_id": batch_id,
                "pipeline_name": pipeline_name,
                "error_code": error_code,
                "payload_hash": payload_hash,
                "metadata": event_metadata,
            },
            profile=canonical_profile,
        )
        entry._events.append(
            QuarantineEntryCreated(
                occurred_at=entry._created_at,
                run_id=run_id,
                batch_id=batch_id,
                pipeline_name=pipeline_name,
                error_code=error_code,
                payload_hash=payload_hash,
                metadata=event_metadata,
                event_id=event_id,
            )
        )

        return entry
