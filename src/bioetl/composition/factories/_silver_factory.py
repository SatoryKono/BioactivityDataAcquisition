"""Silver writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
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
    """Create configured Silver writer."""
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
