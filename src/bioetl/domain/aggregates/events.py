# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Domain Events for Aggregate Coordination.

Domain events represent something that has happened in the domain.
They are immutable, named in past tense, and contain all data needed
for interested parties to react to the event.

Events are collected by aggregates during state transitions and published
by the application layer after successful persistence.

Usage:
    >>> run = PipelineRun(run_id=run_id, run_type=RunType.INCREMENTAL)
    >>> run.start()
    >>> run.complete()
    >>> events = run.collect_events()
    >>> for event in events:
    ...     event_bus.publish(event)
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime

from bioetl.domain.deterministic_identity import deterministic_id
from bioetl.domain.medallion import Layer
from bioetl.domain.types import BatchID, ContentHash, MetaDict, RunID

__all__ = [
    "BatchCreated",
    "BatchFailed",
    "BatchSealed",
    "BatchWritten",
    "DomainEvent",
    "PipelineCompleted",
    "PipelineFailed",
    "PipelineShutdown",
    "QuarantineEntryCreated",
    "QuarantineEntryResolved",
    "RecordQuarantined",
]


def _require_layer(value: object, *, event_name: str) -> Layer:
    if isinstance(value, Layer):
        return value
    raise TypeError(f"{event_name}.layer must be a Layer, got {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events are immutable (frozen) and contain:
    - event_id: Unique identifier for idempotency and event bus integration
    - occurred_at: When the event happened (UTC)
    - run_id: Correlation ID for tracing

    Events are named in past tense to reflect that something has already happened.
    """

    occurred_at: datetime
    event_id: str = field(default="", kw_only=True)

    def __post_init__(self) -> None:
        """Derive event identity from event contents when not explicitly supplied."""
        if self.event_id:
            return
        payload = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "event_id"
        }
        object.__setattr__(
            self,
            "event_id",
            deterministic_id(type(self).__name__, payload),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline Run Events
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PipelineCompleted(DomainEvent):
    """Event: Pipeline run completed successfully.

    Published when a pipeline transitions to COMPLETED status.
    All stages must have succeeded for this event to be emitted.
    """

    run_id: RunID
    pipeline_name: str
    records_processed: int
    duration_seconds: float
    stages_count: int


@dataclass(frozen=True, slots=True)
class PipelineFailed(DomainEvent):
    """Event: Pipeline run failed.

    Published when a pipeline transitions to FAILED status.
    Contains information about the first stage that failed.
    """

    run_id: RunID
    pipeline_name: str
    failed_stage: str
    error: str
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineShutdown(DomainEvent):
    """Event: Pipeline was gracefully shutdown.

    Published when a pipeline receives SIGTERM/SIGINT and
    transitions to SHUTDOWN status.
    """

    run_id: RunID
    pipeline_name: str
    records_processed: int


# ──────────────────────────────────────────────────────────────────────────────
# Batch Events
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BatchCreated(DomainEvent):
    """Event: A new batch has been created.

    Published when a batch is initialized with records.
    """

    run_id: RunID
    batch_id: BatchID
    record_count: int


@dataclass(frozen=True, slots=True)
class BatchSealed(DomainEvent):
    """Event: A batch has been sealed (no more records can be added).

    Published when a batch transitions from OPEN to SEALED status.
    After sealing, the batch is ready for writing to storage.
    """

    run_id: RunID
    batch_id: BatchID
    record_count: int
    valid_count: int
    quarantined_count: int


@dataclass(frozen=True, slots=True)
class BatchWritten(DomainEvent):
    """Event: A batch has been written to storage.

    Published after successful write to Bronze/Silver/Gold layers.
    """

    run_id: RunID
    batch_id: BatchID
    layer: Layer
    record_count: int

    def __post_init__(self) -> None:
        _require_layer(self.layer, event_name=type(self).__name__)
        # Direct call avoids zero-arg super issues with slotted dataclass inheritance.
        DomainEvent.__post_init__(self)


@dataclass(frozen=True, slots=True)
class BatchFailed(DomainEvent):
    """Event: A batch write failed.

    Published when a batch cannot be written to storage.
    The batch may be retried or quarantined.
    """

    run_id: RunID
    batch_id: BatchID
    layer: Layer
    error: str
    error_type: str | None = None

    def __post_init__(self) -> None:
        _require_layer(self.layer, event_name=type(self).__name__)
        # Direct call avoids zero-arg super issues with slotted dataclass inheritance.
        DomainEvent.__post_init__(self)


# ──────────────────────────────────────────────────────────────────────────────
# Quarantine Events
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RecordQuarantined(DomainEvent):
    """Event: A record was sent to quarantine.

    Published when a record fails validation or transformation
    and is isolated for later analysis.
    """

    run_id: RunID
    batch_id: BatchID
    record_id: str | None
    error_code: str | None
    error_message: str
    content_hash: ContentHash | None = None


@dataclass(frozen=True, slots=True)
class QuarantineEntryCreated(DomainEvent):
    """Event: A quarantine entry was created.

    Contains full context about the quarantined record.
    """

    run_id: RunID
    batch_id: BatchID
    pipeline_name: str
    error_code: str
    payload_hash: ContentHash
    metadata: MetaDict | None = None


@dataclass(frozen=True, slots=True)
class QuarantineEntryResolved(DomainEvent):
    """Event: A quarantine entry was resolved.

    Published when a quarantine entry is successfully reprocessed
    or marked as ignored.
    """

    run_id: RunID
    entry_id: str
    resolution: str  # "reprocessed", "ignored"
    resolved_by: str | None = None
