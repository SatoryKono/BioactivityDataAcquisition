"""Runtime dependency resolution helpers for ``GoldWriter``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import (
    NoOpMetadataWriter,
    NoOpTracing,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        LineageStorePort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


@dataclass(frozen=True, slots=True)
class GoldWriterRuntimeServices:
    """Grouped runtime collaborators for ``GoldWriter``."""

    csv_exporter: CsvExporter | None
    tracing: TracingPort
    metrics: MetricsPort | None
    audit: AuditPort | None
    metadata_writer: MetadataWriterPort
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None


def build_gold_writer_runtime_services(
    *,
    csv_exporter: CsvExporter | None,
    tracing: TracingPort | None,
    metrics: MetricsPort | None,
    audit: AuditPort | None,
    metadata_writer: MetadataWriterPort | None,
    metadata_coordinator: MetadataCoordinatorPort | None,
    lineage_store: LineageStorePort | None,
) -> GoldWriterRuntimeServices:
    """Build grouped runtime collaborators while preserving default resolution."""
    return GoldWriterRuntimeServices(
        csv_exporter=csv_exporter,
        tracing=tracing or NoOpTracing(),
        metrics=metrics,
        audit=audit,
        metadata_writer=metadata_writer or NoOpMetadataWriter(),
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
    )
