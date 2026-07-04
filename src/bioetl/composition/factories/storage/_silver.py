"""Silver writer factory helpers for StorageFactory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.delta.resilience import (
        AdaptiveRetryPolicy,
        SilverMergeResiliencePolicy,
    )
    from bioetl.infrastructure.storage.silver_writer import SilverWriter


@dataclass(frozen=True, slots=True)
class CreateSilverWriterRequest:
    """Inputs required to build a configured Silver writer instance."""

    writer_cls: type[SilverWriter]
    base_path: Path
    config: SinkLayerConfig | None
    logger: LoggerPort
    tracing: TracingPort
    csv_exporter: CsvExporter | None
    metadata_coordinator: MetadataCoordinator | None
    audit: AuditPort
    transform_version: str | None
    transform_steps: tuple[str, ...] | None
    flat_structure: bool
    silver_validator: SilverValidatorPort | None
    metrics: MetricsPort | None = None
    metadata_atomic_retry_policy: AdaptiveRetryPolicy | None = None
    merge_resilience_policy: SilverMergeResiliencePolicy | None = None
    contract_rollout_policy: ContractRolloutPolicy | None = None
    pipeline_name: str | None = None


def create_silver_writer(request: CreateSilverWriterRequest) -> SilverWriter:
    """Create configured Silver writer.

    Args:
        writer_cls: SilverWriter class to instantiate.
        base_path: Root directory for Silver layer storage.
        config: Optional sink layer config providing save_metadata flag.
        logger: LoggerPort for structured logging.
        tracing: Explicit TracingPort resolved by composition bootstrap.
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
    save_metadata = request.config.save_metadata if request.config else False
    lineage_store = (
        FileLineageStore(base_path=request.base_path.parent / "control" / "lineage")
        if save_metadata
        else None
    )
    metadata_writer = (
        MetadataWriter(
            logger=request.logger,
            atomic_replace_retry_policy=request.metadata_atomic_retry_policy,
            metrics=request.metrics,
        )
        if save_metadata
        else NoOpMetadataWriter()
    )
    if request.tracing is None:
        raise TypeError(
            "SilverWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    runtime_services = build_silver_writer_runtime_services(
        SilverWriterRuntimeServicesRequest(
            csv_exporter=request.csv_exporter,
            tracing=request.tracing,
            write_policy=None,
            metrics=request.metrics,
            audit=request.audit,
            logger=request.logger,
            silver_validator=request.silver_validator,
            metadata_writer=metadata_writer,
            metadata_coordinator=request.metadata_coordinator,
            lineage_store=lineage_store,
            dq_calculator=None,
            merge_resilience_policy=request.merge_resilience_policy,
            contract_rollout_policy=request.contract_rollout_policy,
            base_path=request.base_path,
            pipeline_name=request.pipeline_name,
        )
    )
    return request.writer_cls(
        base_path=request.base_path,
        logger=request.logger,
        transform_version=request.transform_version,
        transform_steps=request.transform_steps,
        runtime_services=runtime_services,
        pipeline_name=request.pipeline_name,
        flat_structure=request.flat_structure,
    )
