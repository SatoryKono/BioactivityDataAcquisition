"""Runtime dependency resolution helpers for ``SilverWriter``."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.operations.arrow_operations import (
    SilverArrowOperations,
)
from bioetl.infrastructure.storage.silver.operations.delta_operations import (
    SilverDeltaOperations,
)
from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)
from bioetl.infrastructure.storage.silver.operations.merged_operations import (
    SilverMergedOperations,
)
from bioetl.infrastructure.storage.silver.operations.metadata_operations import (
    SilverMetadataOperations,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
    SilverPostwriteOperations,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    SilverValidationOperations,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _deduplicate_by_primary_keys_impl,
    _to_policy_write_mode_impl,
    _validate_key_nullability_impl,
    _validate_write_mode_impl,
)
from bioetl.infrastructure.storage.support.retention import RetentionPolicy
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator

if TYPE_CHECKING:
    import pyarrow as pa


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
    validation_operations: SilverValidationOperations | None = None
    delta_operations: SilverDeltaOperations | None = None
    arrow_operations: SilverArrowOperations | None = None
    merged_operations: SilverMergedOperations | None = None
    postwrite_operations: SilverPostwriteOperations | None = None


@dataclass(frozen=True, slots=True)
class SilverWriterRuntimeServicesRequest:
    """Inputs required to build grouped Silver runtime collaborators."""

    csv_exporter: CsvExporter | None
    tracing: TracingPort | None
    write_policy: WriteModePolicy | None
    metrics: MetricsPort | None
    audit: AuditPort | None
    logger: LoggerPort | None
    silver_validator: SilverValidatorPort | None
    metadata_writer: MetadataWriterPort | None
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None
    dq_calculator: DQMetricsCalculator | None
    merge_resilience_policy: SilverMergeResiliencePolicy | None
    contract_rollout_policy: ContractRolloutPolicy | None = None
    base_path: str | Path | None = None
    pipeline_name: str | None = None


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


def _build_maintenance_operations(
    request: SilverWriterRuntimeServicesRequest,
) -> SilverMaintenanceOperations | None:
    """Create maintenance operations when export and retention inputs exist."""
    if request.csv_exporter is None or request.base_path is None:
        return None
    retention_manager = RetentionPolicy(request.base_path)
    return SilverMaintenanceOperations(
        csv_exporter=request.csv_exporter,
        retention_manager=retention_manager,
        pipeline_name=request.pipeline_name or "silver",
        metrics=request.metrics,
        audit=request.audit,
    )


def _resolve_operation_logger(logger: LoggerPort | None) -> LoggerPort:
    """Resolve an operation-service logger with a safe compatibility fallback."""
    if logger is not None:
        return logger
    return NoOpLogger()


def _build_metadata_operations(
    request: SilverWriterRuntimeServicesRequest,
    *,
    metadata_writer: MetadataWriterPort,
    dq_calculator: DQMetricsCalculator,
) -> SilverMetadataOperations:
    """Create metadata operations bound to resolved metadata and DQ collaborators."""
    logger = _resolve_operation_logger(request.logger)
    return SilverMetadataOperations(
        _logger=logger,
        _metrics=request.metrics,
        _audit=request.audit,
        _metadata_writer=metadata_writer,
        _metadata_coordinator=request.metadata_coordinator,
        _lineage_store=request.lineage_store,
        _dq_calculator=dq_calculator,
        _host=None,  # Will be set later in SilverWriter.__init__
    )


def _build_validation_operations(
    request: SilverWriterRuntimeServicesRequest,
    *,
    write_policy: WriteModePolicy,
    silver_validator: SilverValidatorPort,
) -> SilverValidationOperations | None:
    """Create validation operations when validator and table base path are present."""
    if request.base_path is None:
        return None
    base_path = request.base_path
    logger = _resolve_operation_logger(request.logger)

    # Import here to avoid circular imports
    from bioetl.infrastructure.storage.silver.support import (
        get_table_schema,
        prepare_arrow_data,
        resolve_table_path,
    )

    def _get_table_schema_wrapper(table_name: str) -> Awaitable[pa.Schema | None]:
        """Wrapper for get_table_schema that can be patched in tests."""
        return get_table_schema(base_path, table_name)

    return SilverValidationOperations(
        logger=logger,
        _write_policy=write_policy,
        _metrics=request.metrics,
        _silver_validator=silver_validator,
        _get_table_schema=_get_table_schema_wrapper,
        _resolve_table_path=lambda table_name: resolve_table_path(
            base_path, table_name
        ),
        _prepare_arrow_data=prepare_arrow_data,
        _validate_write_mode=_validate_write_mode_impl,
        _deduplicate_by_primary_keys=_deduplicate_by_primary_keys_impl,
        _to_policy_write_mode=_to_policy_write_mode_impl,
        _validate_key_nullability=_validate_key_nullability_impl,
        _host=None,
    )


def _build_delta_operations(
    request: SilverWriterRuntimeServicesRequest,
    *,
    merge_resilience_policy: SilverMergeResiliencePolicy,
) -> SilverDeltaOperations:
    """Create delta operations around the resolved resilience policy."""
    logger = _resolve_operation_logger(request.logger)
    return SilverDeltaOperations(
        logger=logger,
        _metrics=request.metrics,
        _merge_resilience_policy=merge_resilience_policy,
    )


def _build_merged_operations(
    request: SilverWriterRuntimeServicesRequest,
) -> SilverMergedOperations | None:
    """Create merged-write operations when a table base path is available."""
    if request.base_path is None:
        return None
    base_path = request.base_path
    logger = _resolve_operation_logger(request.logger)

    # Import here to avoid circular imports
    from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
    from bioetl.infrastructure.storage.silver.support import resolve_table_path

    async def _noop_write_silver_merged_metadata(
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: datetime | None,
        run_id: str | None,
        sources_used: list[str] | None,
    ) -> None:
        del (
            table_path,
            table_name,
            records,
            primary_keys,
            completed_at,
            run_id,
            sources_used,
        )
        await asyncio.sleep(0)

    return SilverMergedOperations(
        logger=logger,
        csv_exporter=request.csv_exporter,
        _arrow_converter=ArrowDataConverter(),
        _resolve_table_path=lambda table_name: resolve_table_path(
            base_path, table_name
        ),
        _write_silver_merged_metadata=_noop_write_silver_merged_metadata,
    )


def build_silver_writer_runtime_services(
    request: SilverWriterRuntimeServicesRequest,
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
        tracing=request.tracing,
        write_policy=request.write_policy,
        silver_validator=request.silver_validator,
        metadata_writer=request.metadata_writer,
        dq_calculator=request.dq_calculator,
        merge_resilience_policy=request.merge_resilience_policy,
    )
    maintenance_ops = _build_maintenance_operations(request)
    metadata_ops = _build_metadata_operations(
        request,
        metadata_writer=resolved_metadata_writer,
        dq_calculator=resolved_dq_calculator,
    )
    validation_ops = _build_validation_operations(
        request,
        write_policy=resolved_write_policy,
        silver_validator=resolved_silver_validator,
    )
    delta_ops = _build_delta_operations(
        request,
        merge_resilience_policy=resolved_merge_resilience_policy,
    )
    merged_ops = _build_merged_operations(request)

    return SilverWriterRuntimeServices(
        csv_exporter=request.csv_exporter,
        tracing=resolved_tracing,
        write_policy=resolved_write_policy,
        metrics=request.metrics,
        audit=request.audit,
        silver_validator=resolved_silver_validator,
        metadata_writer=resolved_metadata_writer,
        metadata_coordinator=request.metadata_coordinator,
        lineage_store=request.lineage_store,
        dq_calculator=resolved_dq_calculator,
        merge_resilience_policy=resolved_merge_resilience_policy,
        contract_rollout_policy=request.contract_rollout_policy,
        maintenance_operations=maintenance_ops,
        metadata_operations=metadata_ops,
        validation_operations=validation_ops,
        delta_operations=delta_ops,
        arrow_operations=SilverArrowOperations(),
        merged_operations=merged_ops,
        postwrite_operations=None,
    )
