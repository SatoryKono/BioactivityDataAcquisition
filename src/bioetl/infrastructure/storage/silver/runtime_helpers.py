"""Runtime dependency resolution helpers for ``SilverWriter``."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.support.retention import RetentionPolicy
from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)
from bioetl.infrastructure.storage.silver.operations.metadata_operations import SilverMetadataOperations
from bioetl.infrastructure.storage.silver.operations.validation_operations import SilverValidationOperations
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator


@dataclass(frozen=True, slots=True)
class SilverWriterRuntimeServices:
    """Grouped runtime collaborators for ``SilverWriter``."""

    csv_exporter: CsvExporter | None
    tracing: TracingPort | None
    write_policy: WriteModePolicy
    metrics: MetricsPort | None
    audit: AuditPort | None
    silver_validator: SilverValidatorPort
    metadata_writer: MetadataWriterPort
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None
    dq_calculator: DQMetricsCalculator
    merge_resilience_policy: SilverMergeResiliencePolicy
    contract_rollout_policy: ContractRolloutPolicy | None = None
    # New operation services for composition
    maintenance_operations: SilverMaintenanceOperations | None = None
    metadata_operations: SilverMetadataOperations | None = None


def resolve_silver_writer_runtime(
    *,
    tracing: TracingPort | None,
    write_policy: WriteModePolicy | None,
    silver_validator: SilverValidatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    dq_calculator: DQMetricsCalculator | None,
    merge_resilience_policy: SilverMergeResiliencePolicy | None,
) -> tuple[
    TracingPort | None,
    WriteModePolicy,
    SilverValidatorPort,
    MetadataWriterPort,
    DQMetricsCalculator,
    SilverMergeResiliencePolicy,
]:
    """Resolve default runtime collaborators for ``SilverWriter``."""
    return (
        tracing,
        write_policy or WriteModePolicy(),
        silver_validator or NoOpValidator(),
        metadata_writer or NoOpMetadataWriter(),
        dq_calculator or DQMetricsCalculator(),
        merge_resilience_policy or DEFAULT_SILVER_MERGE_POLICY,
    )


def build_silver_writer_runtime_services(
    *,
    csv_exporter: CsvExporter | None,
    tracing: TracingPort | None,
    write_policy: WriteModePolicy | None,
    metrics: MetricsPort | None,
    audit: AuditPort | None,
    logger: LoggerPort | None,
    silver_validator: SilverValidatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    metadata_coordinator: MetadataCoordinatorPort | None,
    lineage_store: LineageStorePort | None,
    dq_calculator: DQMetricsCalculator | None,
    merge_resilience_policy: SilverMergeResiliencePolicy | None,
    contract_rollout_policy: ContractRolloutPolicy | None = None,
    base_path: str | Path | None = None,
) -> SilverWriterRuntimeServices:
    """Build grouped runtime collaborators while preserving default resolution."""
    (
        resolved_tracing,
        resolved_write_policy,
        resolved_silver_validator,
        resolved_metadata_writer,
        resolved_dq_calculator,
        resolved_merge_resilience_policy,
    ) = resolve_silver_writer_runtime(
        tracing=tracing,
        write_policy=write_policy,
        silver_validator=silver_validator,
        metadata_writer=metadata_writer,
        dq_calculator=dq_calculator,
        merge_resilience_policy=merge_resilience_policy,
    )
    # Create maintenance operations if needed components are available
    maintenance_ops = None
    if csv_exporter is not None and base_path is not None:
        retention_manager = RetentionPolicy(base_path)
        maintenance_ops = SilverMaintenanceOperations(
            csv_exporter=csv_exporter,
            retention_manager=retention_manager,
            metrics=metrics,
            audit=audit,
        )
    
    # Create metadata operations if needed components are available
    metadata_ops = None
    if resolved_metadata_writer is not None and resolved_dq_calculator is not None:
        metadata_ops = SilverMetadataOperations(
            logger=logger,
            metrics=metrics,
            audit=audit,
            metadata_writer=resolved_metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            dq_calculator=resolved_dq_calculator,
        )
    
    return SilverWriterRuntimeServices(
        csv_exporter=csv_exporter,
        tracing=resolved_tracing,
        write_policy=resolved_write_policy,
        metrics=metrics,
        audit=audit,
        silver_validator=resolved_silver_validator,
        metadata_writer=resolved_metadata_writer,
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
        dq_calculator=resolved_dq_calculator,
        merge_resilience_policy=resolved_merge_resilience_policy,
        contract_rollout_policy=contract_rollout_policy,
        maintenance_operations=maintenance_ops,
        metadata_operations=metadata_ops,
    )
