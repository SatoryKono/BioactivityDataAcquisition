"""Gold writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import LoggerPort, TracingPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


def create_gold_writer(
    *,
    writer_cls: type[GoldWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    tracing: TracingPort | None,
    csv_exporter: CsvExporter | None,
    metadata_coordinator: MetadataCoordinator | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
    flat_structure: bool,
) -> GoldWriter:
    """Create configured Gold writer."""
    save_metadata = config.save_metadata if config else False
    metadata_writer = (
        MetadataWriter(logger=logger) if save_metadata else NoOpMetadataWriter()
    )
    effective_tracing: TracingPort = tracing or NoOpTracing()
    return writer_cls(
        base_path=base_path,
        logger=logger,
        tracing=effective_tracing,
        csv_exporter=csv_exporter,
        metadata_writer=metadata_writer,
        metadata_coordinator=metadata_coordinator,
        transform_version=transform_version,
        transform_steps=transform_steps,
        flat_structure=flat_structure,
    )
