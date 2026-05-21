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


def _resolve_legacy_or_service(
    legacy_kwargs: dict[str, object],
    *,
    key: str,
    services: PipelineServicesProtocol | None,
    service_attr: str | None = None,
) -> object | None:
    """Resolve collaborator from legacy kwargs first, then service container."""
    resolved = legacy_kwargs.get(key)
    if resolved is not None:
        return resolved
    if services is None:
        return None
    return cast("object | None", getattr(services, service_attr or key, None))


def resolve_postrun_collaborators(
    *,
    services: PipelineServicesProtocol | None,
    context: PipelineContext,
    legacy_kwargs: dict[str, object],
) -> ResolvedPostrunCollaborators:
    """Resolve storage/metrics/logger/metadata collaborators for PostrunService."""
    resolved_storage = _resolve_legacy_or_service(
        legacy_kwargs,
        key="storage",
        services=services,
    )
    resolved_logger = _resolve_legacy_or_service(
        legacy_kwargs,
        key="logger",
        services=services,
    )
    if resolved_logger is None:
        resolved_logger = context.logger

    if resolved_storage is None or resolved_logger is None:
        raise AssertionError(
            "PostrunService requires storage and logger (provide services or legacy kwargs)"
        )

    resolved_metrics = _resolve_legacy_or_service(
        legacy_kwargs,
        key="metrics",
        services=services,
    )
    if resolved_metrics is None:
        raise AssertionError(
            "PostrunService requires metrics (provide services or legacy kwargs)"
        )

    resolved_metadata_coordinator = _resolve_legacy_or_service(
        legacy_kwargs,
        key="metadata_coordinator",
        services=services,
    )
    resolved_metadata_writer = _resolve_legacy_or_service(
        legacy_kwargs,
        key="metadata_writer",
        services=services,
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
