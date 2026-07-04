"""Canonical SilverWriter metadata helper facade."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal, cast

import polars as pl
import pyarrow as pa
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.dq_metrics import (
    BatchDQMetrics,
    ColumnStats,
    SchemaDriftInfo,
)
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
    _prepare_silver_metadata_write,
    _read_delta_version,
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _SilverMetadataAuditSupportRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.silver.operations.metadata_operations import (
        SilverMetadataOperations,
    )


class SilverWriterMetadataFacade:
    """Writer-level metadata helper methods backed by composition services."""

    _metadata: SilverMetadataOperations | None

    _SILVER_METADATA_OPERATIONS_REQUIRED = "Silver metadata operations are required"

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get the schema of an existing Silver table."""
        return await BaseDeltaWriter._get_table_schema(
            cast(BaseDeltaWriter, self), table_name
        )

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between an existing table and incoming records."""
        from bioetl.infrastructure.storage.silver.schema_drift_operations import (
            _build_schema_drift_info,
            _build_silver_schema_drift_diff,
        )

        existing_schema = await self._get_table_schema(table_name)
        diff = _build_silver_schema_drift_diff(existing_schema, records)
        return None if diff is None else _build_schema_drift_info(diff)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Resolve current Delta version for one Silver table."""
        try:
            return await asyncio.to_thread(_read_delta_version, table_path)
        except DeltaTableNotFoundError:
            return None

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: pl.DataFrame | list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute batch DQ metrics with schema drift information."""
        frame = (
            records
            if isinstance(records, pl.DataFrame)
            else pl.from_dicts(
                records,
                strict=False,
                infer_schema_length=None,
            )
        )
        valid_records = len(frame)
        column_stats = {
            column: self._compute_column_stats(frame[column], valid_records)
            for column in frame.columns
            if column
            not in {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        }
        normalized_records = (
            frame.to_dicts() if isinstance(records, pl.DataFrame) else records
        )
        return BatchDQMetrics(
            total_records=valid_records + quarantined_count,
            valid_records=valid_records,
            error_records=quarantined_count,
            column_stats=column_stats,
            schema_drift=await self._detect_schema_drift(
                table_name, normalized_records
            ),
            validation_errors=tuple(validation_errors or ()),
        )

    @staticmethod
    def _compute_column_stats(series: pl.Series, valid_records: int) -> ColumnStats:
        """Compute bounded DQ stats for one Silver metadata column."""
        numeric_values = [
            float(value)
            for value in series.drop_nulls().to_list()
            if isinstance(value, int | float) and not isinstance(value, bool)
        ]
        return ColumnStats(
            null_rate=(series.null_count() / valid_records) if valid_records else 0.0,
            unique_count=series.n_unique(),
            min_value=min(numeric_values) if numeric_values else None,
            max_value=max(numeric_values) if numeric_values else None,
            mean_value=(sum(numeric_values) / len(numeric_values))
            if numeric_values
            else None,
        )

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
    ) -> bool:
        """Return whether canonical Silver metadata publication should short-circuit."""
        metadata_writer = getattr(self, "_metadata_writer", None)
        if not records:
            return True
        if isinstance(metadata_writer, NoOpMetadataWriter):
            return True
        if getattr(self, "_metadata_coordinator", None) is None:
            raise RuntimeError(
                "MetadataCoordinator with create_silver_metadata_bundle is required "
                "for Silver metadata publication"
            )
        return False

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None:
        """Publish canonical Silver metadata through metadata operations."""
        if self._metadata is None:
            raise RuntimeError(self._SILVER_METADATA_OPERATIONS_REQUIRED)
        if self._should_skip_silver_metadata_write(records=request.records):
            return
        await _execute_silver_metadata_write(
            cast(_SilverMetadataWriteHostProtocol, self),
            request=request,
            prepare=_prepare_silver_metadata_write,
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
        """Persist one Silver metadata sidecar through metadata operations."""
        if self._metadata is None:
            raise RuntimeError(self._SILVER_METADATA_OPERATIONS_REQUIRED)
        await self._metadata._write_silver_metadata_file(
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: Literal["append", "merge", "overwrite", "delete"] | SilverWriteMode,
        *,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Log Silver audit events through metadata operations."""
        if self._metadata is None:
            raise RuntimeError(self._SILVER_METADATA_OPERATIONS_REQUIRED)
        validated_mode = (
            mode if isinstance(mode, SilverWriteMode) else SilverWriteMode(mode)
        )
        await self._metadata._log_silver_audit(
            _SilverMetadataAuditSupportRequest(
                table_name=table_name,
                records=records,
                mode=validated_mode,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
            )
        )

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before metadata persistence."""
        dq_metrics = await self._compute_dq_metrics(
            request.table_name,
            request.records,
            quarantined_count=request.quarantined_count or 0,
            validation_errors=request.validation_errors,
        )
        from bioetl.infrastructure.storage.silver import metadata_mixin

        return _PreparedSilverWriteFinalizationContext(
            dq_metrics=dq_metrics,
            version_after=await self._get_delta_version(request.table_path),
            completed_at=request.started_at
            + timedelta(
                seconds=metadata_mixin.time.perf_counter() - request.start_perf
            ),
        )

    async def _finalize_silver_write_result(
        self,
        request: _SilverWriteResultFinalizationRequest,
    ) -> SilverWriteResult | None:
        """Finalize Silver write metadata/result through canonical helper methods."""
        context = await self._prepare_silver_write_finalization_context(
            _SilverWriteFinalizationPreparationRequest(
                table_name=request.table_name,
                records=request.records,
                table_path=request.table_path,
                quarantined_count=request.quarantined_count,
                validation_errors=request.validation_errors,
                primary_keys=request.primary_keys,
                validated_mode=request.validated_mode,
                started_at=request.started_at,
                start_perf=request.start_perf,
            )
        )
        await self._write_silver_metadata(
            _SilverMetadataWriteRequest(
                table_path=request.table_path,
                table_name=request.table_name,
                records=request.records,
                primary_keys=request.primary_keys,
                mode=request.validated_mode,
                bronze_refs=request.bronze_refs,
                dq_metrics=context.dq_metrics,
                partition_by=request.partition_cols,
                source_batch_ids=(
                    [str(request.source_batch_id)] if request.source_batch_id else None
                ),
                started_at=request.started_at,
                completed_at=context.completed_at,
                version_after=context.version_after,
            )
        )
        return (
            None
            if context.version_after is None
            else SilverWriteResult(
                table_name=request.table_name,
                table_path=request.table_path,
                delta_version=context.version_after,
                record_count=len(request.records),
            )
        )
