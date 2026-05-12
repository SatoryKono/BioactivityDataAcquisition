"""Metadata operations facade for Silver layer lineage, audit, and DQ writes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _PreparedSilverWriteFinalizationContext,
    _SilverMetadataWriteRequest,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_audit_operations import (
    log_internal_silver_audit_operation,
    log_silver_audit_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_dq_operations import (
    compute_silver_dq_metrics_operation,
    get_flat_structure,
    get_transform_steps,
    get_transform_version,
    persist_silver_metadata_operation,
    resolve_finalization_dq_metrics_operation,
    resolve_silver_manifest_id,
    resolve_version_after_operation,
    should_skip_silver_metadata_write_operation,
    write_silver_metadata_file_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_operations import (
    finalize_silver_write_result_operation,
    prepare_silver_write_finalization_context_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_operations import (
    write_internal_silver_metadata_operation,
    write_silver_merged_metadata_operation,
    write_silver_metadata_via_support_request,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _SilverMetadataAuditSupportRequest,
)

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = ["SilverMetadataOperations", "_execute_silver_metadata_write"]


@dataclass(frozen=True, slots=True)
class SilverMetadataOperations:
    """Silver-layer metadata operations via composition."""

    _logger: LoggerPort
    _metrics: MetricsPort | None = None
    _audit: AuditPort | None = None
    _metadata_writer: MetadataWriterPort | None = None
    _metadata_coordinator: MetadataCoordinatorPort | None = None
    _lineage_store: LineageStorePort | None = None
    _dq_calculator: DQMetricsCalculator | None = None
    _host: object | None = None

    @property
    def _flat_structure(self) -> bool:
        """Resolve flat-structure metadata mode from the current host, if any."""
        return get_flat_structure(self)

    @property
    def _transform_version(self) -> str | None:
        """Resolve transform version from the current host, if any."""
        return get_transform_version(self)

    @property
    def _transform_steps(self) -> tuple[str, ...]:
        """Resolve transform steps from the current host with a stable fallback."""
        return get_transform_steps(self)

    def _resolve_manifest_id(self, *, records: list[BronzeRecord]) -> str | None:
        """Resolve control-plane manifest id from records, host, or coordinator."""
        return resolve_silver_manifest_id(self, records=records)

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None:
        """Persist metadata using whichever writer signature is available."""
        return await persist_silver_metadata_operation(
            self,
            metadata=metadata,
            table_name=table_name,
            table_path=table_path,
        )

    async def _resolve_finalization_dq_metrics(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Resolve DQ metrics via host override when present, otherwise compute them."""
        return await resolve_finalization_dq_metrics_operation(
            self,
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def _resolve_version_after(self, table_path: str) -> int | None:
        """Read Delta version via host helper when available."""
        return await resolve_version_after_operation(self, table_path)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Compatibility hook expected by canonical metadata helpers."""
        return await self._resolve_version_after(table_path)

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compatibility hook expected by canonical finalization helpers."""
        return await self._resolve_finalization_dq_metrics(
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def compute_dq_metrics(
        self,
        arrow_data: pa.Table,
        *,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for Silver write."""
        return await compute_silver_dq_metrics_operation(
            self,
            arrow_data,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool:
        """Return whether canonical Silver metadata publication should short-circuit."""
        return should_skip_silver_metadata_write_operation(
            self,
            records=records,
            table_path=table_path,
            event_name=event_name,
        )

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist one canonical Silver metadata sidecar through the writer port."""
        await write_silver_metadata_file_operation(
            self,
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None:
        """Canonical Silver metadata publication path for composition-backed ops."""
        await write_internal_silver_metadata_operation(
            self,
            request,
            execute_silver_metadata_write=_execute_silver_metadata_write,
        )

    async def _write_silver_merged_metadata(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Canonical Silver metadata publication path for merged composite writes."""
        await write_silver_merged_metadata_operation(
            self,
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            execute_silver_metadata_write=_execute_silver_metadata_write,
        )

    async def write_silver_metadata(
        self,
        table_name: str,
        dq_metrics: BatchDQMetrics,
        records: list[BronzeRecord],
        bronze_refs: list[BronzeWriteResult] | None = None,
        mode: str = "merge",
        validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> SilverWriteResult | None:
        """Write metadata for Silver layer."""
        return await write_silver_metadata_via_support_request(
            self,
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

    async def log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Log Silver write audit event."""
        await log_silver_audit_operation(
            self,
            table_name=table_name,
            records=records,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            error=error,
        )

    async def _log_silver_audit(
        self,
        request: _SilverMetadataAuditSupportRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Backward compatibility alias for log_silver_audit."""
        await log_internal_silver_audit_operation(
            self,
            request,
            args=args,
            kwargs=kwargs,
        )

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest | None = None,
        *args: object,
        perf_counter: Callable[[], float] | None = None,
        **kwargs: object,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        return await prepare_silver_write_finalization_context_operation(
            self,
            request,
            args=args,
            perf_counter=perf_counter,
            kwargs=kwargs,
        )

    async def _finalize_silver_write_result(
        self,
        request: _SilverWriteResultFinalizationRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        return await finalize_silver_write_result_operation(
            self,
            request,
            args=args,
            kwargs=kwargs,
        )
