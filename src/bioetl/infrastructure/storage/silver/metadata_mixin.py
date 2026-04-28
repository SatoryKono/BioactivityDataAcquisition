"""Metadata and audit helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMetadataMixin"]

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Protocol

import pyarrow as pa
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LoggerPort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _build_silver_write_result,
    _coerce_silver_metadata_write_request,
    _execute_silver_metadata_write,
    _prepare_silver_merged_metadata_write,
    _prepare_silver_metadata_write,
    _prepare_silver_write_finalization_context,
    _PreparedSilverWriteFinalizationContext,
    _read_delta_version,
    _SilverMetadataWriteHostProtocol,
    _SilverMetadataWriteRequest,
    _SilverWriteFinalizationHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _build_silver_merged_metadata_write_request,
    _coerce_silver_write_finalization_preparation_request,
    _coerce_silver_write_result_finalization_request,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _log_silver_audit_event,
    _SilverMetadataAuditSupportRequest,
)


class _SilverWriterMetadataRuntimeProtocol(
    _SilverMetadataWriteHostProtocol,
    _SilverWriteFinalizationHostProtocol,
    Protocol,
):
    """Full runtime contract expected by ``SilverWriterMetadataMixin`` methods."""

    logger: LoggerPort
    _audit: AuditPort | None
    _dq_calculator: DQMetricsCalculator
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]


class SilverWriterMetadataMixin:
    """Mixin with metadata, lineage, and audit helpers."""

    async def _compute_dq_metrics(
        self: _SilverWriterMetadataRuntimeProtocol,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute DQ metrics using injected calculator."""
        from bioetl.domain.services.dq_metrics_calculator import DQMetricsInput

        existing_schema = await self._get_table_schema(table_name)
        existing_fields: set[str] | None = None
        if existing_schema is not None:
            existing_fields = set(existing_schema.names)

        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
            quarantined_count=quarantined_count,
            validation_errors=list(validation_errors) if validation_errors else None,
        )
        return self._dq_calculator.calculate(input_data)

    async def _log_silver_audit(
        self: _SilverWriterMetadataRuntimeProtocol,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        *,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Log audit entry for Silver write operation."""
        await _log_silver_audit_event(
            self,
            _SilverMetadataAuditSupportRequest(
                table_name=table_name,
                records=records,
                mode=mode,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
            ),
        )

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version, if table exists."""
        try:
            version = await asyncio.to_thread(_read_delta_version, table_path)
            return version
        except DeltaTableNotFoundError:
            return None

    def _should_skip_silver_metadata_write(
        self: _SilverWriterMetadataRuntimeProtocol,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool:
        """Return whether Silver metadata write should short-circuit before prepare."""
        if not records:
            return True
        if isinstance(self._metadata_writer, NoOpMetadataWriter):
            return True
        if self._metadata_coordinator is None:
            raise RuntimeError(
                "MetadataCoordinator with create_silver_metadata_bundle is required "
                f"for Silver metadata publication: event={event_name}, "
                f"table_path={table_path}"
            )
        return False

    async def _write_silver_metadata(
        self: _SilverWriterMetadataRuntimeProtocol,
        request: _SilverMetadataWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Write Silver layer metadata sidecar file."""
        resolved_request = _coerce_silver_metadata_write_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        if self._should_skip_silver_metadata_write(
            records=resolved_request.records,
            table_path=resolved_request.table_path,
            event_name="silver_metadata_skipped",
        ):
            return
        await _execute_silver_metadata_write(
            self,
            request=resolved_request,
            prepare=_prepare_silver_metadata_write,
        )

    async def _write_silver_merged_metadata(
        self: _SilverWriterMetadataRuntimeProtocol,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write Silver metadata sidecar for merged composite data."""
        if self._should_skip_silver_metadata_write(
            records=records,
            table_path=table_path,
            event_name="silver_merged_metadata_skipped",
        ):
            return
        request_kwargs = {
            "table_path": table_path,
            "table_name": table_name,
            "records": records,
            "primary_keys": primary_keys,
        }
        request_kwargs["completed_at"] = completed_at
        request_kwargs["run_id"] = run_id
        request_kwargs["sources_used"] = sources_used
        await _execute_silver_metadata_write(
            self,
            request=_build_silver_merged_metadata_write_request(**request_kwargs),
            prepare=_prepare_silver_merged_metadata_write,
        )

    async def _write_silver_metadata_file(
        self: _SilverWriterMetadataRuntimeProtocol,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist one Silver metadata sidecar via the canonical writer handoff."""
        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _maybe_log_silver_audit(
        self: _SilverWriterMetadataRuntimeProtocol,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Guard for audit logging — only calls _log_silver_audit if enabled."""
        if self._audit and records:
            await self._log_silver_audit(
                table_name=table_name,
                records=records,
                mode=mode,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
            )

    async def _finalize_silver_write_result(
        self: _SilverWriterMetadataRuntimeProtocol,
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
        context = await self._prepare_silver_write_finalization_context(
            table_name=resolved_request.table_name,
            records=resolved_request.records,
            table_path=resolved_request.table_path,
            quarantined_count=resolved_request.quarantined_count,
            validation_errors=resolved_request.validation_errors,
            started_at=resolved_request.started_at,
            start_perf=resolved_request.start_perf,
        )

        await self._write_silver_metadata(
            table_path=resolved_request.table_path,
            table_name=resolved_request.table_name,
            records=resolved_request.records,
            primary_keys=resolved_request.primary_keys,
            mode=resolved_request.validated_mode,
            bronze_refs=resolved_request.bronze_refs,
            dq_metrics=context.dq_metrics,
            partition_by=resolved_request.partition_cols,
            source_batch_ids=(
                [str(resolved_request.source_batch_id)]
                if resolved_request.source_batch_id is not None
                else None
            ),
            started_at=resolved_request.started_at,
            completed_at=context.completed_at,
            version_after=context.version_after,
        )
        return _build_silver_write_result(
            table_name=resolved_request.table_name,
            table_path=resolved_request.table_path,
            version_after=context.version_after,
            records_count=len(resolved_request.records),
        )

    async def _prepare_silver_write_finalization_context(
        self: _SilverWriterMetadataRuntimeProtocol,
        request: _SilverWriteFinalizationPreparationRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        resolved_request = _coerce_silver_write_finalization_preparation_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        return await _prepare_silver_write_finalization_context(
            self,
            resolved_request,
            perf_counter=time.perf_counter,
        )
