"""Canonical mapping from typed Domain Events to runtime observability events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

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

_PIPELINE_LIFECYCLE_FAMILY = "pipeline.lifecycle"


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
    handler = _DOMAIN_EVENT_BUILDERS.get(type(event))
    if handler is None:
        raise TypeError(
            f"Unsupported DomainEvent for observability mapping: {type(event).__name__}"
        )
    return handler(event)


DomainEventBuilder = Callable[[DomainEvent], DomainEventObservabilityEnvelope]


def _build_envelope(
    *,
    event_name: str,
    severity: str,
    event_family: str,
    phase_hint: str,
    context: dict[str, object],
) -> DomainEventObservabilityEnvelope:
    return DomainEventObservabilityEnvelope(
        event_name=event_name,
        severity=severity,
        event_family=event_family,
        phase_hint=phase_hint,
        context=context,
    )


def _build_pipeline_completed(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(PipelineCompleted, event)
    return _build_envelope(
        event_name=PipelineEvent.COMPLETE,
        severity="info",
        event_family=_PIPELINE_LIFECYCLE_FAMILY,
        phase_hint="cleanup",
        context={
            "run_id": str(typed.run_id),
            "pipeline": typed.pipeline_name,
            "records_processed": typed.records_processed,
            "duration_seconds": typed.duration_seconds,
            "stages_count": typed.stages_count,
        },
    )


def _build_pipeline_failed(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(PipelineFailed, event)
    return _build_envelope(
        event_name=PipelineEvent.FAILED,
        severity="error",
        event_family=_PIPELINE_LIFECYCLE_FAMILY,
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "pipeline": typed.pipeline_name,
            "failed_stage": typed.failed_stage,
            "error": typed.error,
            "error_type": typed.error_type or "unknown",
        },
    )


def _build_pipeline_shutdown(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(PipelineShutdown, event)
    return _build_envelope(
        event_name=PipelineEvent.SHUTDOWN,
        severity="warning",
        event_family=_PIPELINE_LIFECYCLE_FAMILY,
        phase_hint="cleanup",
        context={
            "run_id": str(typed.run_id),
            "pipeline": typed.pipeline_name,
            "records_processed": typed.records_processed,
        },
    )


def _build_batch_created(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(BatchCreated, event)
    return _build_envelope(
        event_name="batch_created",
        severity="info",
        event_family="batch",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "batch_id": str(typed.batch_id),
            "record_count": typed.record_count,
        },
    )


def _build_batch_sealed(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(BatchSealed, event)
    return _build_envelope(
        event_name="batch_sealed",
        severity="info",
        event_family="batch",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "batch_id": str(typed.batch_id),
            "record_count": typed.record_count,
            "valid_count": typed.valid_count,
            "quarantined_count": typed.quarantined_count,
        },
    )


def _build_batch_written(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(BatchWritten, event)
    return _build_envelope(
        event_name="batch_written",
        severity="info",
        event_family="batch",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "batch_id": str(typed.batch_id),
            "layer": typed.layer,
            "record_count": typed.record_count,
        },
    )


def _build_batch_failed(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(BatchFailed, event)
    return _build_envelope(
        event_name="batch_failed",
        severity="error",
        event_family="batch",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "batch_id": str(typed.batch_id),
            "layer": typed.layer,
            "error": typed.error,
            "error_type": typed.error_type or "unknown",
        },
    )


def _build_record_quarantined(event: DomainEvent) -> DomainEventObservabilityEnvelope:
    typed = cast(RecordQuarantined, event)
    content_hash = typed.content_hash
    return _build_envelope(
        event_name="record_quarantined",
        severity="warning",
        event_family="quarantine",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "batch_id": str(typed.batch_id),
            "record_id": typed.record_id,
            "error_code": typed.error_code,
            "error": typed.error_message,
            "content_hash": str(content_hash) if content_hash is not None else None,
        },
    )


def _build_quarantine_entry_created(
    event: DomainEvent,
) -> DomainEventObservabilityEnvelope:
    typed = cast(QuarantineEntryCreated, event)
    return _build_envelope(
        event_name="quarantine_entry_created",
        severity="warning",
        event_family="quarantine",
        phase_hint="execution",
        context={
            "run_id": str(typed.run_id),
            "pipeline": typed.pipeline_name,
            "batch_id": str(typed.batch_id),
            "error_code": typed.error_code,
            "payload_hash": str(typed.payload_hash),
            "metadata": typed.metadata,
        },
    )


def _build_quarantine_entry_resolved(
    event: DomainEvent,
) -> DomainEventObservabilityEnvelope:
    typed = cast(QuarantineEntryResolved, event)
    return _build_envelope(
        event_name="quarantine_entry_resolved",
        severity="info",
        event_family="quarantine",
        phase_hint="postrun",
        context={
            "run_id": str(typed.run_id),
            "entry_id": typed.entry_id,
            "resolution": typed.resolution,
            "resolved_by": typed.resolved_by,
        },
    )


_DOMAIN_EVENT_BUILDERS: dict[type[DomainEvent], DomainEventBuilder] = {
    PipelineCompleted: _build_pipeline_completed,
    PipelineFailed: _build_pipeline_failed,
    PipelineShutdown: _build_pipeline_shutdown,
    BatchCreated: _build_batch_created,
    BatchSealed: _build_batch_sealed,
    BatchWritten: _build_batch_written,
    BatchFailed: _build_batch_failed,
    RecordQuarantined: _build_record_quarantined,
    QuarantineEntryCreated: _build_quarantine_entry_created,
    QuarantineEntryResolved: _build_quarantine_entry_resolved,
}
