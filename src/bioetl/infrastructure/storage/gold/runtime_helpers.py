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
        MetadataCoordinatorPort,
        MetadataWriterPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


@dataclass(frozen=True, slots=True)
class GoldWriterRuntimeServices:
    """Grouped runtime collaborators for ``GoldWriter``."""

    csv_exporter: CsvExporter | None
    tracing: TracingPort
    audit: AuditPort | None
    metadata_writer: MetadataWriterPort
    metadata_coordinator: MetadataCoordinatorPort | None


def build_gold_writer_runtime_services(
    *,
    csv_exporter: CsvExporter | None,
    tracing: TracingPort | None,
    audit: AuditPort | None,
    metadata_writer: MetadataWriterPort | None,
    metadata_coordinator: MetadataCoordinatorPort | None,
) -> GoldWriterRuntimeServices:
    """Build grouped runtime collaborators while preserving default resolution."""
    return GoldWriterRuntimeServices(
        csv_exporter=csv_exporter,
        tracing=tracing or NoOpTracing(),
        audit=audit,
        metadata_writer=metadata_writer or NoOpMetadataWriter(),
        metadata_coordinator=metadata_coordinator,
    )
