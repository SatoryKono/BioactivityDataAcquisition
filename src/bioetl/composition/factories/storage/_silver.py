"""Silver writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.application.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.silver_writer import SilverWriter
    from bioetl.infrastructure.storage.write_resilience import (
        AdaptiveRetryPolicy,
        SilverMergeResiliencePolicy,
    )


def create_silver_writer(
    *,
    writer_cls: type[SilverWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    tracing: TracingPort | None,
    csv_exporter: CsvExporter | None,
    metadata_coordinator: MetadataCoordinator | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
    flat_structure: bool,
    silver_validator: SilverValidatorPort | None,
    metrics: MetricsPort | None = None,
    metadata_atomic_retry_policy: AdaptiveRetryPolicy | None = None,
    merge_resilience_policy: SilverMergeResiliencePolicy | None = None,
) -> SilverWriter:
    """Create configured Silver writer.

    Args:
        writer_cls: SilverWriter class to instantiate.
        base_path: Root directory for Silver layer storage.
        config: Optional sink layer config providing save_metadata flag.
        logger: LoggerPort for structured logging.
        tracing: Optional TracingPort; defaults to NoOpTracing if None.
        csv_exporter: Optional CSV exporter for parallel Silver CSV output.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        transform_version: Transform version tag written to Silver metadata.
        transform_steps: Ordered transform step labels for metadata.
        flat_structure: If True, writes files without provider/entity subdirectories.
        silver_validator: Optional PyArrow schema validator for Silver records.
        metrics: Optional MetricsPort for metadata writer; defaults to None.
        metadata_atomic_retry_policy: Optional retry policy for atomic metadata
            replace operations; defaults to None.
        merge_resilience_policy: Optional timeout/retry policy for Delta merge
            operations; defaults to None.

    Returns:
        Configured SilverWriter instance for the Silver storage layer.
    """
    save_metadata = config.save_metadata if config else False
    metadata_writer = (
        MetadataWriter(
            logger=logger,
            atomic_replace_retry_policy=metadata_atomic_retry_policy,
            metrics=metrics,
        )
        if save_metadata
        else NoOpMetadataWriter()
    )
    effective_tracing: TracingPort = tracing or NoOpTracing()
    return writer_cls(
        base_path=base_path,
        logger=logger,
        tracing=effective_tracing,
        csv_exporter=csv_exporter,
        silver_validator=silver_validator,
        metadata_writer=metadata_writer,
        metadata_coordinator=metadata_coordinator,
        transform_version=transform_version,
        transform_steps=transform_steps,
        flat_structure=flat_structure,
        merge_resilience_policy=merge_resilience_policy,
    )
