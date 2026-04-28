"""Mixins that keep the ``SilverWriter`` write API stable."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, cast

import polars as pl
import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.ports import SilverWriteRequest, coerce_silver_write_request
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics, SchemaDriftInfo
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.merged_mixin import (
    SilverWriterMergedMixin,
)
from bioetl.infrastructure.storage.silver.merged_operations import (
    _build_merged_silver_write_request,
    _execute_merged_silver_write_flow,
    _MergedSilverWriteRequest,
    _PreparedMergedSilverWrite,
)
from bioetl.infrastructure.storage.silver.metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver.operations.merged_operations import (
    SilverMergedOperations,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    SilverValidationOperations,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
)
from bioetl.infrastructure.storage.silver.validation_mixin import (
    SilverWriterValidationMixin,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)


def _normalize_completed_at(value: datetime | str) -> datetime:
    """Normalize compatibility timestamps into aware datetimes."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class SilverWriterDQCompatibilityMixin:
    """Compatibility surface for Silver DQ and schema helper methods."""

    _validation: SilverValidationOperations | None

    def _as_validation_mixin(self) -> SilverWriterValidationMixin:
        """Treat this compatibility host as a validation-mixin implementation."""
        return cast("SilverWriterValidationMixin", self)

    def _resolve_table_path(self, table_name: str) -> str:
        """Resolve the physical table path for one Silver table."""
        from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

        return BaseDeltaWriter._resolve_table_path(
            cast("BaseDeltaWriter", self),
            table_name,
        )

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

        SilverWriterValidationMixin._validate_silver_pandera(
            self._as_validation_mixin(),
            records,
            table_name,
        )

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
            self._as_validation_mixin(),
            table_name,
            records,
            on_schema_mismatch,
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
        records: pl.DataFrame | list[dict[str, object]],
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
            from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

            return await BaseDeltaWriter._get_table_schema(
                cast("BaseDeltaWriter", self),
                table_name,
            )
        except (
            AttributeError,
            ImportError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            return None


class SilverWriterMergedCompatibilityMixin:
    """Compatibility surface for merged-write helpers."""

    _merged: SilverMergedOperations | None

    def _as_merged_mixin(self) -> SilverWriterMergedMixin:
        """Treat this compatibility host as a merged-mixin implementation."""
        return cast("SilverWriterMergedMixin", self)

    def _as_metadata_mixin(self) -> SilverWriterMetadataMixin:
        """Treat this compatibility host as a metadata-mixin implementation."""
        return cast("SilverWriterMetadataMixin", self)

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
        request_kwargs = {
            "table_name": table_name,
            "records": records,
            "primary_keys": primary_keys,
            "completed_at": completed_at,
            "run_id": run_id,
            "sources_used": sources_used,
            "preserve_column_order": preserve_column_order,
        }
        if self._merged is not None:
            await _execute_merged_silver_write_flow(
                self._merged,
                _build_merged_silver_write_request(**request_kwargs),
            )
            return

        from bioetl.infrastructure.storage.silver.merged_mixin import (
            SilverWriterMergedMixin,
        )

        await SilverWriterMergedMixin.write_silver_merged(
            self._as_merged_mixin(),
            **request_kwargs,
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

        return SilverWriterMergedMixin._prepare_merged_silver_write(
            self._as_merged_mixin(),
            request,
        )

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
            self._as_merged_mixin(),
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
            self._as_merged_mixin(),
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

        normalized_completed_at = (
            _normalize_completed_at(completed_at) if completed_at is not None else None
        )

        await SilverWriterMetadataMixin._write_silver_merged_metadata(
            self._as_metadata_mixin(),
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

    def _should_dual_write(self) -> bool:
        """Return whether the writer should fan out to multiple targets."""
        raise NotImplementedError

    async def _write_single_target(
        self,
        *,
        invocation: _SilverWriteInvocation | None = None,
        **legacy_kwargs: object,
    ) -> SilverWriteResult | None:
        """Write one Silver target."""
        del invocation, legacy_kwargs
        await asyncio.sleep(0)
        raise NotImplementedError

    async def _write_dual_targets(
        self,
        *,
        invocation: _SilverWriteInvocation | None = None,
        **legacy_kwargs: object,
    ) -> SilverWriteResult | None:
        """Write all configured Silver targets."""
        del invocation, legacy_kwargs
        await asyncio.sleep(0)
        raise NotImplementedError

    async def _prepare_silver_write_payload(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> _PreparedSilverWritePayload:
        """Prepare validated Silver payload for downstream write dispatch."""
        del (
            table_name,
            records,
            primary_keys,
            schema,
            mode,
            on_schema_mismatch,
            column_order,
            partition_cols,
            key_nullability_rules,
        )
        await asyncio.sleep(0)
        raise NotImplementedError

    async def _dispatch_write_with_domain_errors(
        self,
        *,
        table_name: str,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch the underlying Delta write."""
        del table_name, request
        await asyncio.sleep(0)
        raise NotImplementedError

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run post-dispatch pipeline completion."""
        del ctx, payload
        await asyncio.sleep(0)
        raise NotImplementedError

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
