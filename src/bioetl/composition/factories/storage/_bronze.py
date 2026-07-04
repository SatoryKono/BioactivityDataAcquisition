"""Bronze writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.bronze_writer import BronzeWriterRuntimeServices
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
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
    audit: AuditPort,
    flat_structure: bool,
) -> BronzeWriter:
    """Create configured Bronze writer.

    Args:
        writer_cls: BronzeWriter class to instantiate.
        base_path: Root directory for Bronze layer storage.
        config: Optional sink layer config providing save_json and save_metadata flags.
        logger: LoggerPort for structured logging.
        metrics: MetricsPort for recording storage metrics.
        tracing: TracingPort resolved by composition bootstrap.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        flat_structure: If True, writes files without provider/entity subdirectories.

    Returns:
        Configured BronzeWriter instance for the Bronze storage layer.
    """
    save_json = config.save_json if config else False
    save_metadata = config.save_metadata if config else False
    if save_metadata and metadata_coordinator is None:
        raise RuntimeError(
            "Bronze metadata publication requires MetadataCoordinator when "
            "save_metadata is enabled."
        )
    lineage_store = (
        FileLineageStore(base_path=base_path.parent / "control" / "lineage")
        if save_metadata
        else None
    )
    metadata_writer = (
        MetadataWriter(logger=logger) if save_metadata else NoOpMetadataWriter()
    )
    if tracing is None:
        raise TypeError(
            "BronzeWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    return writer_cls(
        base_path=base_path,
        logger=logger,
        metrics=metrics,
        save_json=save_json,
        json_path=None,
        runtime_services=BronzeWriterRuntimeServices(
            tracing=tracing,
            audit=audit,
            metadata_writer=metadata_writer,
            save_metadata=save_metadata,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
        flat_structure=flat_structure,
    )
