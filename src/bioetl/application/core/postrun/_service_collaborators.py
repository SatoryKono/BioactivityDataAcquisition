"""Private collaborator-resolution helpers for the postrun service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_aux_service_protocols import (
        PipelinePostrunServicesProtocol,
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

def resolve_postrun_collaborators(
    *,
    services: PipelinePostrunServicesProtocol | None,
    context: PipelineContext,
) -> ResolvedPostrunCollaborators:
    """Resolve storage/metrics/logger/metadata collaborators from services."""
    if services is None:
        raise AssertionError("PostrunService requires services")

    resolved_storage = cast(object | None, getattr(services, "storage", None))
    resolved_logger = cast(object | None, getattr(services, "logger", None))
    if resolved_logger is None:
        resolved_logger = context.logger

    if resolved_storage is None or resolved_logger is None:
        raise AssertionError("PostrunService requires storage and logger via services")

    resolved_metrics = cast(object | None, getattr(services, "metrics", None))
    if resolved_metrics is None:
        raise AssertionError("PostrunService requires metrics via services")

    resolved_metadata_coordinator = cast(
        object | None,
        getattr(services, "metadata_coordinator", None),
    )
    resolved_metadata_writer = cast(
        object | None,
        getattr(services, "metadata_writer", None),
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
