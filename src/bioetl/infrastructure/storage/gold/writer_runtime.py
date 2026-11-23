"""Runtime services resolution for Gold writer."""

from __future__ import annotations

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)

__all__ = ["_resolve_runtime_services"]


def _resolve_runtime_services(
    *,
    runtime_services: GoldWriterRuntimeServices | None,
) -> GoldWriterRuntimeServices:
    """Resolve Gold runtime services; enabled metadata requires a coordinator."""
    services = runtime_services or build_gold_writer_runtime_services(
        csv_exporter=None,
        tracing=None,
        metrics=None,
        audit=None,
        metadata_writer=None,
        metadata_coordinator=None,
        lineage_store=None,
    )
    if not isinstance(services.metadata_writer, NoOpMetadataWriter) and (
        services.metadata_coordinator is None
    ):
        raise ValueError("Gold metadata writer requires a metadata coordinator")
    return services
