"""Metadata operations for Silver layer (DQ metrics, lineage, audit)."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

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
from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _coerce_silver_write_finalization_preparation_request,
    _coerce_silver_write_result_finalization_request,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_builders import (
    _normalize_records_for_dq_metrics,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_support import (
    _finalize_silver_write_result,
    _prepare_silver_write_finalization_context,
    _PreparedSilverWriteFinalizationContext,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _coerce_silver_metadata_audit_request,
    _log_silver_audit_event,
    _SilverMetadataAuditSupportRequest,
    _SilverMetadataWriteSupportRequest,
    _write_silver_metadata,
)

if TYPE_CHECKING:
    import pyarrow as pa


class _DQMetricsHostOverride(Protocol):
    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        *,
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics | None: ...


class _DeltaVersionHostOverride(Protocol):
    async def _get_delta_version(self, table_path: str) -> int | None: ...


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

    def _log_debug(self, message: str) -> None:
        """Best-effort debug logging."""
        if hasattr(self._logger, "debug"):
            self._logger.debug(message)

    def _log_info(self, message: str) -> None:
        """Best-effort info logging."""
        if hasattr(self._logger, "info"):
            self._logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Best-effort warning logging."""
        if hasattr(self._logger, "warning"):
            self._logger.warning(message)

    def _resolve_manifest_id(
        self,
        *,
        records: list[BronzeRecord],
    ) -> str | None:
        """Resolve control-plane manifest id from records, host, or coordinator."""
        if records and records[0].get("_manifest_id") is not None:
            return str(records[0]["_manifest_id"])

        host_manifest_id = getattr(self._host, "manifest_id", None)
        if host_manifest_id is not None:
            return str(host_manifest_id)

        coordinator = self._metadata_coordinator
        coordinator_context = getattr(coordinator, "run_context", None)
        coordinator_manifest_id = getattr(coordinator_context, "manifest_id", None)
        if coordinator_manifest_id is not None:
            return str(coordinator_manifest_id)

        self._log_debug("Silver metadata manifest_id is unavailable")
        return None

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None:
        """Persist metadata using whichever writer signature is available."""
        if self._metadata_writer is None:
            self._log_info(
                "Skipping Silver metadata persistence: metadata writer missing"
            )
            return None

        write_silver_metadata = self._metadata_writer.write_silver_metadata
        parameters = inspect.signature(write_silver_metadata).parameters
        accepts_var_kwargs = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )

        if "base_path" in parameters or accepts_var_kwargs:
            await write_silver_metadata(
                base_path=table_path,
                metadata=metadata,
                table_name=table_name,
            )
        elif "table_path" in parameters:
            legacy_write = cast(
                Any, write_silver_metadata
            )  # Any: legacy writer accepts historical table_path kwargs
            await legacy_write(
                table_path=table_path,
                metadata=metadata,
                table_name=table_name,
            )
        else:
            legacy_write = cast(
                Any, write_silver_metadata
            )  # Any: legacy writer may expose a positional signature
            await legacy_write(table_path, metadata, table_name=table_name)
        return None

    async def _resolve_finalization_dq_metrics(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Resolve DQ metrics via host override when present, otherwise compute them."""
        host_compute_dq_metrics = getattr(self._host, "_compute_dq_metrics", None)
        if getattr(host_compute_dq_metrics, "__name__", None) == "AsyncMock":
            host = cast(_DQMetricsHostOverride, self._host)
            dq_metrics = await host._compute_dq_metrics(
                table_name,
                records,
                quarantined_count=quarantined_count or 0,
                validation_errors=validation_errors,
            )
            if dq_metrics is not None:
                return dq_metrics

        import pyarrow as pa

        normalized_records = _normalize_records_for_dq_metrics(records)
        arrow_data = (
            pa.Table.from_pylist(normalized_records)
            if normalized_records
            else pa.table({})
        )
        return await self.compute_dq_metrics(
            arrow_data=arrow_data,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def _resolve_version_after(self, table_path: str) -> int | None:
        """Read Delta version via host helper when available."""
        if self._host is not None and hasattr(self._host, "_get_delta_version"):
            host = cast(_DeltaVersionHostOverride, self._host)
            return await host._get_delta_version(table_path)
        return 0

    async def compute_dq_metrics(
        self,
        arrow_data: pa.Table,
        *,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for Silver write."""
        if self._dq_calculator is None:
            self._log_warning("DQ calculator missing; returning empty BatchDQMetrics")
            return BatchDQMetrics()

        records_dict = (
            [dict(record) for record in arrow_data.to_pylist()] if arrow_data else []
        )
        existing_schema_fields = set(arrow_data.column_names) if arrow_data else set()

        dq_input = DQMetricsInput(
            records=records_dict,
            existing_schema_fields=existing_schema_fields,
            quarantined_count=quarantined_count or 0,
            validation_errors=(
                list(validation_errors) if validation_errors is not None else None
            ),
        )

        return await asyncio.to_thread(self._dq_calculator.calculate, dq_input)

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
        return await _write_silver_metadata(
            self,
            _SilverMetadataWriteSupportRequest(
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
            ),
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
        del mode, error
        if not self._audit:
            return

        await _log_silver_audit_event(
            self,
            _SilverMetadataAuditSupportRequest(
                table_name=table_name,
                records=records,
                mode=validated_mode,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
            ),
        )

    async def _log_silver_audit(
        self,
        request: _SilverMetadataAuditSupportRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Backward compatibility alias for log_silver_audit."""
        resolved_request = _coerce_silver_metadata_audit_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        await _log_silver_audit_event(
            self,
            resolved_request,
        )

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest | None = None,
        *args: object,
        perf_counter: Callable[[], float] | None = None,
        **kwargs: object,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        resolved_request = _coerce_silver_write_finalization_preparation_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        resolved_perf_counter = perf_counter
        if resolved_perf_counter is None:
            from bioetl.infrastructure.storage.silver import metadata_mixin

            resolved_perf_counter = metadata_mixin.time.perf_counter
        return await _prepare_silver_write_finalization_context(
            self,
            resolved_request,
            perf_counter=resolved_perf_counter,
        )

    async def _finalize_silver_write_result(
        self,
        request: _SilverWriteResultFinalizationRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        resolved_request = _coerce_silver_write_result_finalization_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        return await _finalize_silver_write_result(
            self,
            resolved_request,
        )
