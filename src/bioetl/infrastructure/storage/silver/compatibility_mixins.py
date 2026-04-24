"""Mixins that keep the ``SilverWriter`` write API stable."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import polars as pl
import pyarrow as pa

from bioetl.domain.ports import SilverWriteRequest, coerce_silver_write_request
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.silver.merged_operations import (
    _MergedSilverWriteRequest,
    _PreparedMergedSilverWrite,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
)

if TYPE_CHECKING:
    from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics, SchemaDriftInfo
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


def _normalize_completed_at(value: datetime | str) -> datetime:
    """Normalize compatibility timestamps into aware datetimes."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class SilverWriterDQCompatibilityMixin:
    """Compatibility surface for Silver DQ and schema helper methods."""

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Delegate Pandera validation to the validation service."""
        if self._validation:
            self._validation._validate_silver_pandera(records, table_name)
            return

        from bioetl.infrastructure.storage.silver.validation_mixin import (
            SilverWriterValidationMixin,
        )

        SilverWriterValidationMixin._validate_silver_pandera(self, records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Delegate schema-drift handling to the validation service."""
        if self._validation:
            await self._validation._check_schema_drift(
                table_name, records, on_schema_mismatch
            )
            return

        from bioetl.infrastructure.storage.silver.validation_mixin import (
            SilverWriterValidationMixin,
        )

        await SilverWriterValidationMixin._check_schema_drift(
            self, table_name, records, on_schema_mismatch
        )

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
    ) -> SchemaDriftInfo | None:
        """Backward compatibility method for schema drift detection."""
        from bioetl.infrastructure.storage.silver.schema_drift_operations import (
            _build_schema_drift_info,
            _build_silver_schema_drift_diff,
        )

        existing_schema = await self._get_table_schema(table_name)
        diff = _build_silver_schema_drift_diff(existing_schema, records)
        if diff is None:
            return None
        return _build_schema_drift_info(diff)

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: pl.DataFrame | list[dict],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for a batch of records."""
        from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics, ColumnStats

        if isinstance(records, list):
            records = pl.DataFrame(records)

        valid_records = len(records)
        total_records = valid_records + quarantined_count
        error_records = quarantined_count

        internal_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        column_stats = {}
        for col_name in records.columns:
            if col_name in internal_fields:
                continue
            col_data = records[col_name]
            column_stats[col_name] = {
                "null_count": col_data.null_count(),
                "unique_count": col_data.n_unique(),
            }

        records_list = (
            records.to_dicts() if isinstance(records, pl.DataFrame) else records
        )
        schema_drift = await self._detect_schema_drift(table_name, records_list)

        records_length = len(records) if hasattr(records, "__len__") else records.height
        column_stats_objects = {
            col_name: ColumnStats(
                null_rate=stats["null_count"] / records_length
                if records_length > 0
                else 0.0,
                unique_count=stats["unique_count"],
                min_value=None,
                max_value=None,
                mean_value=None,
            )
            for col_name, stats in column_stats.items()
        }

        return BatchDQMetrics(
            total_records=total_records,
            valid_records=valid_records,
            error_records=error_records,
            column_stats=column_stats_objects,
            schema_drift=schema_drift,
            validation_errors=tuple(validation_errors or ()),
        )

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get the schema of an existing Silver table."""
        try:
            from deltalake.exceptions import (
                TableNotFoundError as DeltaTableNotFoundError,
            )

            from bioetl.infrastructure.storage.base_delta_writer import (
                DeltaTable as PatchedDeltaTable,
            )

            table_path = self._resolve_table_path(table_name)
            dt = PatchedDeltaTable(table_path)
            return dt.schema().to_arrow()
        except DeltaTableNotFoundError:
            return None
        except (
            AttributeError,
            ImportError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            return await super()._get_table_schema(table_name)


class SilverWriterMergedCompatibilityMixin:
    """Compatibility surface for merged-write helpers."""

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged Silver records through the merged-write service surface."""
        if self._merged is not None:
            await self._merged.write_silver_merged(
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                completed_at=completed_at,
                run_id=run_id,
                sources_used=sources_used,
                preserve_column_order=preserve_column_order,
            )
            return

        from bioetl.infrastructure.storage.silver.merged_mixin import (
            SilverWriterMergedMixin,
        )

        await SilverWriterMergedMixin.write_silver_merged(
            self,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    def _prepare_merged_silver_write(
        self,
        request: _MergedSilverWriteRequest,
    ) -> _PreparedMergedSilverWrite:
        """Compatibility seam for merged payload preparation."""
        if self._merged is not None:
            return self._merged._prepare_merged_silver_write(request)

        from bioetl.infrastructure.storage.silver.merged_mixin import (
            SilverWriterMergedMixin,
        )

        return SilverWriterMergedMixin._prepare_merged_silver_write(self, request)

    async def _write_silver_merged_delta(
        self,
        *,
        table_path: str,
        arrow_table: pa.Table,
    ) -> None:
        """Compatibility seam for merged Delta overwrite execution."""
        if self._merged is not None:
            await self._merged._write_silver_merged_delta(
                table_path=table_path,
                arrow_table=arrow_table,
            )
            return

        from bioetl.infrastructure.storage.silver.merged_mixin import (
            SilverWriterMergedMixin,
        )

        await SilverWriterMergedMixin._write_silver_merged_delta(
            self,
            table_path=table_path,
            arrow_table=arrow_table,
        )

    async def _export_silver_merged_csv(
        self,
        *,
        table_name: str,
        arrow_table: pa.Table,
    ) -> None:
        """Compatibility seam for merged CSV export."""
        if self._merged is not None:
            await self._merged._export_silver_merged_csv(
                table_name=table_name,
                arrow_table=arrow_table,
            )
            return

        from bioetl.infrastructure.storage.silver.merged_mixin import (
            SilverWriterMergedMixin,
        )

        await SilverWriterMergedMixin._export_silver_merged_csv(
            self,
            table_name=table_name,
            arrow_table=arrow_table,
        )

    async def _write_silver_merged_metadata(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: str | datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged Silver metadata for a completed table write."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        normalized_completed_at = completed_at
        if completed_at is not None:
            normalized_completed_at = _normalize_completed_at(completed_at)

        await SilverWriterMetadataMixin._write_silver_merged_metadata(
            self,
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=normalized_completed_at,
            run_id=run_id,
            sources_used=sources_used,
        )


class SilverWriterWriteCompatibilityMixin:
    """Compatibility surface for the main Silver write entrypoints."""

    async def write_silver(
        self,
        request: SilverWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Write normalized records to Silver layer."""
        write_request = coerce_silver_write_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        table_name = write_request.table_name
        records = write_request.records
        primary_keys = write_request.primary_keys
        schema = write_request.schema
        mode = write_request.mode
        partition_cols = write_request.partition_cols
        on_schema_mismatch = write_request.on_schema_mismatch
        column_order = write_request.column_order
        bronze_refs = write_request.bronze_refs
        key_nullability_rules = write_request.key_nullability_rules
        run_id = write_request.run_id
        run_type = write_request.run_type
        source_batch_id = write_request.source_batch_id
        ingestion_ts = write_request.ingestion_ts
        quarantined_count = write_request.quarantined_count
        validation_errors = write_request.validation_errors
        if not self._should_dual_write():
            return await self._write_single_target(
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                schema=schema,
                mode=mode,
                partition_cols=partition_cols,
                on_schema_mismatch=on_schema_mismatch,
                column_order=column_order,
                bronze_refs=bronze_refs,
                key_nullability_rules=key_nullability_rules,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
                quarantined_count=quarantined_count,
                validation_errors=validation_errors,
            )

        return await self._write_dual_targets(
            logical_table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            bronze_refs=bronze_refs,
            key_nullability_rules=key_nullability_rules,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def _execute_silver_write_pipeline(
        self,
        *,
        invocation: _SilverWriteInvocation,
        ctx: _SilverWriteExecutionContext,
    ) -> SilverWriteResult | None:
        """Orchestrate the Silver write pipeline stages."""
        return await execute_silver_write_pipeline(
            invocation=invocation,
            ctx=ctx,
            prepare_payload=self._prepare_silver_write_payload,
            dispatch_write=self._dispatch_write_with_domain_errors,
            complete_pipeline=self._complete_silver_write_pipeline,
        )
