"""Bronze writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


def create_bronze_writer(
    *,
    writer_cls: type[BronzeWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    flat_structure: bool,
) -> BronzeWriter:
    """Create configured Bronze writer.

    Returns:
        Configured BronzeWriter instance for the Bronze storage layer.
    """
    save_json = config.save_json if config else False
    save_metadata = config.save_metadata if config else False
    metadata_writer = (
        MetadataWriter(logger=logger) if save_metadata else NoOpMetadataWriter()
    )
    effective_tracing: TracingPort = tracing or NoOpTracing()
    return writer_cls(
        base_path=base_path,
        logger=logger,
        metrics=metrics,
        tracing=effective_tracing,
        save_json=save_json,
        json_path=None,
        metadata_writer=metadata_writer,
        save_metadata=save_metadata,
        metadata_coordinator=metadata_coordinator,
        flat_structure=flat_structure,
    )
