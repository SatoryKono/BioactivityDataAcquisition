"""Shared helpers for publishing typed domain events through observability ports."""

from __future__ import annotations

from bioetl.domain.observability_contract import build_observability_contract_payload
from bioetl.domain.observability_event_mapping import (
    map_domain_event_to_observability_event,
)
from bioetl.domain.types import RunType

from .observer_event_mixin import _ObserverEventMixin

if False:  # pragma: no cover
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = ["publish_domain_event_via_ports"]


def _derive_provider_name(pipeline_name: str) -> str:
    if "_" not in pipeline_name:
        return pipeline_name
    provider, _entity = pipeline_name.split("_", 1)
    return provider or pipeline_name


def publish_domain_event_via_ports(
    event: DomainEvent,
    *,
    pipeline_name: str,
    logger: LoggerPort,
    metrics: MetricsPort,
    run_type: RunType | None = None,
) -> None:
    """Publish one typed domain event without requiring a full PipelineObserver."""
    envelope = map_domain_event_to_observability_event(event)
    severity = _ObserverEventMixin._normalize_severity(envelope.severity)
    payload = build_observability_contract_payload(
        event_name=envelope.event_name,
        context={
            "event_family": envelope.event_family,
            "occurred_at": event.occurred_at.isoformat(),
            **envelope.context,
        },
        default_provider=_derive_provider_name(pipeline_name),
        default_pipeline=pipeline_name,
        default_run_id=str(getattr(event, "run_id", "unknown")),
        default_severity=severity,
        correlation_defaults={
            "run_type": run_type.value if run_type is not None else None,
        },
    )
    log_context = dict(payload.context)
    log_context.pop("event", None)
    log_method = getattr(logger, severity, logger.info)
    log_method(envelope.event_name, **log_context)
    metrics.increment_counter(
        "observability_events_total",
        1,
        labels=payload.metric_labels,
    )
