# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Metadata and audit helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMetadataMixin", "time"]

import asyncio
import time
from collections.abc import Callable, Sequence
from datetime import datetime

from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_mixin_protocols import (
    _SilverWriterMetadataRuntimeProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
    _prepare_silver_merged_metadata_write,
    _prepare_silver_metadata_write,
    _read_delta_version,
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_operations import (
    finalize_silver_write_result_operation,
    prepare_silver_write_finalization_context_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _log_silver_audit_event,
    _SilverMetadataAuditSupportRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _build_silver_merged_metadata_write_request,
    _PreparedSilverWriteFinalizationContext,
)


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
        from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsInput

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

    async def _get_delta_version(
        self: _SilverWriterMetadataRuntimeProtocol,
        table_path: str,
    ) -> int | None:
        """Get current Delta table version, if table exists."""
        try:
            return await asyncio.to_thread(_read_delta_version, table_path)
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
        request: _SilverMetadataWriteRequest,
    ) -> None:
        """Write Silver layer metadata sidecar file."""
        if self._should_skip_silver_metadata_write(
            records=request.records,
            table_path=request.table_path,
            event_name="silver_metadata_skipped",
        ):
            return
        await _execute_silver_metadata_write(
            self,
            request=request,
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
        await _execute_silver_metadata_write(
            self,
            request=_build_silver_merged_metadata_write_request(
                table_path=table_path,
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                completed_at=completed_at,
                run_id=run_id,
                sources_used=sources_used,
            ),
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
        request: _SilverWriteResultFinalizationRequest,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        return await finalize_silver_write_result_operation(
            self,
            request,
        )

    async def _prepare_silver_write_finalization_context(
        self: _SilverWriterMetadataRuntimeProtocol,
        request: _SilverWriteFinalizationPreparationRequest,
        *,
        perf_counter: Callable[[], float] | None = None,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        return await prepare_silver_write_finalization_context_operation(
            self,
            request,
            perf_counter=perf_counter or time.perf_counter,
        )
