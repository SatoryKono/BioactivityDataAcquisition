"""Private collaborator-resolution helpers for the postrun service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_service_protocols import (
        PipelineServicesProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        StorageMaintenancePort,
    )


@dataclass(frozen=True, slots=True)
class ResolvedPostrunCollaborators:
    """Resolved postrun collaborators after legacy/service fallback lookup."""

    storage: StorageMaintenancePort
    metrics: MetricsPort
    logger: LoggerPort
    metadata_coordinator: MetadataCoordinatorPort | None
    metadata_writer: MetadataWriterPort | None


def _resolve_explicit_or_service(
    explicit_value: object | None,
    *,
    services: PipelineServicesProtocol | None,
    key: str,
    service_attr: str | None = None,
) -> object | None:
    """Resolve collaborator from explicit constructor value, then service container."""
    if explicit_value is not None:
        return explicit_value
    if services is None:
        return None
    return cast("object | None", getattr(services, service_attr or key, None))


def resolve_postrun_collaborators(
    *,
    services: PipelineServicesProtocol | None,
    context: PipelineContext,
    storage: object | None = None,
    metrics: object | None = None,
    logger: object | None = None,
    metadata_coordinator: object | None = None,
    metadata_writer: object | None = None,
) -> ResolvedPostrunCollaborators:
    """Resolve storage/metrics/logger/metadata collaborators for PostrunService.

    Compatibility shim for legacy direct constructor kwargs. Review for removal
    after 2026-09-30 once callers rely on ``services=...`` exclusively.
    """
    resolved_storage = _resolve_explicit_or_service(
        storage,
        services=services,
        key="storage",
    )
    resolved_logger = _resolve_explicit_or_service(
        logger,
        services=services,
        key="logger",
    )
    if resolved_logger is None:
        resolved_logger = context.logger

    if resolved_storage is None or resolved_logger is None:
        raise AssertionError(
            "PostrunService requires storage and logger (provide services or legacy kwargs)"
        )

    resolved_metrics = _resolve_explicit_or_service(
        metrics,
        services=services,
        key="metrics",
    )
    if resolved_metrics is None:
        raise AssertionError(
            "PostrunService requires metrics (provide services or legacy kwargs)"
        )

    resolved_metadata_coordinator = _resolve_explicit_or_service(
        metadata_coordinator,
        services=services,
        key="metadata_coordinator",
    )
    resolved_metadata_writer = _resolve_explicit_or_service(
        metadata_writer,
        services=services,
        key="metadata_writer",
    )
    return ResolvedPostrunCollaborators(
        storage=cast("StorageMaintenancePort", resolved_storage),
        metrics=cast("MetricsPort", resolved_metrics),
        logger=cast("LoggerPort", resolved_logger),
        metadata_coordinator=cast(
            "MetadataCoordinatorPort | None",
            resolved_metadata_coordinator,
        ),
        metadata_writer=cast("MetadataWriterPort | None", resolved_metadata_writer),
    )
