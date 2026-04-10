"""Canonical mapping from typed Domain Events to runtime observability events."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.aggregates.events import (
    BatchCreated,
    BatchFailed,
    BatchSealed,
    BatchWritten,
    DomainEvent,
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
    QuarantineEntryCreated,
    QuarantineEntryResolved,
    RecordQuarantined,
)
from bioetl.domain.events import PipelineEvent

__all__ = [
    "DomainEventObservabilityEnvelope",
    "map_domain_event_to_observability_event",
]


@dataclass(frozen=True, slots=True)
class DomainEventObservabilityEnvelope:
    """One canonical observability projection for a typed domain event."""

    event_name: str
    severity: str
    event_family: str
    phase_hint: str | None = None
    context: dict[str, object] = field(default_factory=dict)


def map_domain_event_to_observability_event(
    event: DomainEvent,
) -> DomainEventObservabilityEnvelope:
    """Project a typed domain event into the runtime observability vocabulary."""
    match event:
        case PipelineCompleted():
            return DomainEventObservabilityEnvelope(
                event_name=PipelineEvent.COMPLETE,
                severity="info",
                event_family="pipeline.lifecycle",
                phase_hint="cleanup",
                context={
                    "run_id": str(event.run_id),
                    "pipeline": event.pipeline_name,
                    "records_processed": event.records_processed,
                    "duration_seconds": event.duration_seconds,
                    "stages_count": event.stages_count,
                },
            )
        case PipelineFailed():
            return DomainEventObservabilityEnvelope(
                event_name=PipelineEvent.FAILED,
                severity="error",
                event_family="pipeline.lifecycle",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "pipeline": event.pipeline_name,
                    "failed_stage": event.failed_stage,
                    "error": event.error,
                    "error_type": event.error_type or "unknown",
                },
            )
        case PipelineShutdown():
            return DomainEventObservabilityEnvelope(
                event_name=PipelineEvent.SHUTDOWN,
                severity="warning",
                event_family="pipeline.lifecycle",
                phase_hint="cleanup",
                context={
                    "run_id": str(event.run_id),
                    "pipeline": event.pipeline_name,
                    "records_processed": event.records_processed,
                },
            )
        case BatchCreated():
            return DomainEventObservabilityEnvelope(
                event_name="batch_created",
                severity="info",
                event_family="batch",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "batch_id": str(event.batch_id),
                    "record_count": event.record_count,
                },
            )
        case BatchSealed():
            return DomainEventObservabilityEnvelope(
                event_name="batch_sealed",
                severity="info",
                event_family="batch",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "batch_id": str(event.batch_id),
                    "record_count": event.record_count,
                    "valid_count": event.valid_count,
                    "quarantined_count": event.quarantined_count,
                },
            )
        case BatchWritten():
            return DomainEventObservabilityEnvelope(
                event_name="batch_written",
                severity="info",
                event_family="batch",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "batch_id": str(event.batch_id),
                    "layer": event.layer,
                    "record_count": event.record_count,
                },
            )
        case BatchFailed():
            return DomainEventObservabilityEnvelope(
                event_name="batch_failed",
                severity="error",
                event_family="batch",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "batch_id": str(event.batch_id),
                    "layer": event.layer,
                    "error": event.error,
                    "error_type": event.error_type or "unknown",
                },
            )
        case RecordQuarantined():
            return DomainEventObservabilityEnvelope(
                event_name="record_quarantined",
                severity="warning",
                event_family="quarantine",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "batch_id": str(event.batch_id),
                    "record_id": event.record_id,
                    "error_code": event.error_code,
                    "error": event.error_message,
                    "content_hash": (
                        str(event.content_hash) if event.content_hash is not None else None
                    ),
                },
            )
        case QuarantineEntryCreated():
            return DomainEventObservabilityEnvelope(
                event_name="quarantine_entry_created",
                severity="warning",
                event_family="quarantine",
                phase_hint="execution",
                context={
                    "run_id": str(event.run_id),
                    "pipeline": event.pipeline_name,
                    "batch_id": str(event.batch_id),
                    "error_code": event.error_code,
                    "payload_hash": str(event.payload_hash),
                    "metadata": event.metadata,
                },
            )
        case QuarantineEntryResolved():
            return DomainEventObservabilityEnvelope(
                event_name="quarantine_entry_resolved",
                severity="info",
                event_family="quarantine",
                phase_hint="postrun",
                context={
                    "run_id": str(event.run_id),
                    "entry_id": event.entry_id,
                    "resolution": event.resolution,
                    "resolved_by": event.resolved_by,
                },
            )
        case _:
            raise TypeError(
                f"Unsupported DomainEvent for observability mapping: {type(event).__name__}"
            )
