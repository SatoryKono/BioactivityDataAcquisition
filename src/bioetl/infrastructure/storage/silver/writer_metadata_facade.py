"""Canonical SilverWriter metadata helper facade."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Literal, cast

import polars as pl
import pyarrow as pa
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import (
    BatchDQMetrics,
    ColumnStats,
    SchemaDriftInfo,
)
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter
from bioetl.infrastructure.storage.silver.metadata_operations import _read_delta_version


class SilverWriterMetadataFacade:
    """Writer-level metadata helper methods backed by composition services."""

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get the schema of an existing Silver table."""
        return await BaseDeltaWriter._get_table_schema(self, table_name)

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
        frame = records if isinstance(records, pl.DataFrame) else pl.DataFrame(records)
        valid_records = len(frame)
        column_stats = {
            column: ColumnStats(
                null_rate=(frame[column].null_count() / valid_records)
                if valid_records
                else 0.0,
                unique_count=frame[column].n_unique(),
            )
            for column in frame.columns
            if column
            not in {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        }
        normalized_records = (
            cast(list[BronzeRecord], frame.to_dicts())
            if isinstance(records, pl.DataFrame)
            else records
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

    async def _write_silver_metadata(
        self,
        request: object | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Publish canonical Silver metadata through metadata operations."""
        if self._metadata is None:
            raise RuntimeError("Silver metadata operations are required")
        await self._metadata._write_silver_metadata(request, *args, **kwargs)  # type: ignore[arg-type]

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
            raise RuntimeError("Silver metadata operations are required")
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
            raise RuntimeError("Silver metadata operations are required")
        validated_mode = (
            mode if isinstance(mode, SilverWriteMode) else SilverWriteMode(mode)
        )
        await self._metadata._log_silver_audit(
            table_name=table_name,
            records=records,
            mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )

    async def _prepare_silver_write_finalization_context(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
        started_at: datetime,
        start_perf: float,
    ) -> object:
        """Prepare DQ/version/timing context before metadata persistence."""
        dq_metrics = await self._compute_dq_metrics(
            table_name,
            records,
            quarantined_count=quarantined_count or 0,
            validation_errors=validation_errors,
        )
        from bioetl.infrastructure.storage.silver import metadata_mixin
        from bioetl.infrastructure.storage.silver.metadata_request_models import (
            _PreparedSilverWriteFinalizationContext,
        )

        return _PreparedSilverWriteFinalizationContext(
            dq_metrics=dq_metrics,
            version_after=await self._get_delta_version(table_path),
            completed_at=started_at
            + timedelta(seconds=metadata_mixin.time.perf_counter() - start_perf),
        )

    async def _finalize_silver_write_result(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        primary_keys: list[str],
        validated_mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None,
        partition_cols: list[str] | None,
        source_batch_id: BatchID | None,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None:
        """Finalize Silver write metadata/result through canonical helper methods."""
        context = await self._prepare_silver_write_finalization_context(
            table_name=table_name,
            records=records,
            table_path=table_path,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
            started_at=started_at,
            start_perf=start_perf,
        )
        await self._write_silver_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            mode=validated_mode,
            bronze_refs=bronze_refs,
            dq_metrics=context.dq_metrics,
            partition_by=partition_cols,
            source_batch_ids=([str(source_batch_id)] if source_batch_id else None),
            started_at=started_at,
            completed_at=context.completed_at,
            version_after=context.version_after,
        )
        return (
            None
            if context.version_after is None
            else SilverWriteResult(
                table_name=table_name,
                table_path=table_path,
                delta_version=context.version_after,
                record_count=len(records),
            )
        )
