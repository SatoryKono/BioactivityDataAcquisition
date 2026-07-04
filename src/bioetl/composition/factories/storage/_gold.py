"""Gold writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
)
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


def create_gold_writer(
    *,
    writer_cls: type[GoldWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    tracing: TracingPort,
    csv_exporter: CsvExporter | None,
    metadata_coordinator: MetadataCoordinator | None,
    audit: AuditPort,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
    flat_structure: bool,
    metrics: MetricsPort | None = None,
    contract_rollout_policy: ContractRolloutPolicy | None = None,
) -> GoldWriter:
    """Create configured Gold writer.

    Args:
        writer_cls: GoldWriter class to instantiate.
        base_path: Root directory for Gold layer storage.
        config: Optional sink layer config providing save_metadata flag.
        logger: LoggerPort for structured logging.
        tracing: Explicit TracingPort resolved by composition bootstrap.
        csv_exporter: Optional CSV exporter for parallel Gold CSV output.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        transform_version: Transform version tag written to Gold metadata.
        transform_steps: Ordered transform step labels for metadata.
        flat_structure: If True, writes files without provider/entity subdirectories.

    Returns:
        Configured GoldWriter instance for the Gold storage layer.
    """
    save_metadata = config.save_metadata if config else False
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
            "GoldWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    return writer_cls(
        base_path=base_path,
        logger=logger,
        transform_version=transform_version,
        transform_steps=transform_steps,
        runtime_services=GoldWriterRuntimeServices(
            csv_exporter=csv_exporter,
            tracing=tracing,
            metrics=metrics,
            audit=audit,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            contract_rollout_policy=contract_rollout_policy,
        ),
        flat_structure=flat_structure,
    )
