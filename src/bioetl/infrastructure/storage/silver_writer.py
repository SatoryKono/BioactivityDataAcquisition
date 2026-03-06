"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from deltalake import DeltaTable
from deltalake import write_deltalake as _write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError

from bioetl.domain.exceptions import MergeConflictError, SchemaViolationError
from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord, MetaDict
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
)
from bioetl.infrastructure.storage.silver_writer_arrow_mixin import (
    SilverWriterArrowMixin,
)
from bioetl.infrastructure.storage.silver_writer_delta_mixin import (
    SilverWriterDeltaMixin,
)
from bioetl.infrastructure.storage.silver_writer_merged_mixin import (
    SilverWriterMergedMixin,
)
from bioetl.infrastructure.storage.silver_writer_metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver_writer_validation_mixin import (
    SilverWriterValidationMixin,
)
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)

# Backward-compatible module aliases for tests patching historical symbols.
asyncio = _asyncio
write_deltalake = _write_deltalake

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.export.csv_exporter import CsvExporter

__all__ = ["SilverWriteMode", "SilverWriter"]


@dataclass(frozen=True, slots=True)
class _SilverWriteExecutionContext:
    table_name: str
    primary_keys: list[str]
    schema: pa.Schema
    mode: str
    partition_cols: list[str] | None
    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    column_order: list[str] | None
    bronze_refs: list[BronzeWriteResult] | None
    key_nullability_rules: list[KeyNullabilityRule] | None
    started_at: datetime
    start_perf: float
    span: Any  # Any: OpenTelemetry span interface is runtime-dependent


class SilverWriter(  # type: ignore[misc]  # Callable vs async-def in MRO
    SilverWriterArrowMixin,
    SilverWriterValidationMixin,
    SilverWriterDeltaMixin,
    SilverWriterMetadataMixin,
    SilverWriterMergedMixin,
    BaseDeltaWriter,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        csv_exporter: CsvExporter | None = None,
        write_policy: WriteModePolicy | None = None,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        silver_validator: SilverValidatorPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        flat_structure: bool = False,
        dq_calculator: DQMetricsCalculator | None = None,
        merge_resilience_policy: SilverMergeResiliencePolicy | None = None,
    ) -> None:
        """Initialize Silver writer."""
        super().__init__(base_path, logger, flat_structure=flat_structure)
        self._dq_calculator = dq_calculator or DQMetricsCalculator()
        self._merge_resilience_policy = (
            merge_resilience_policy or DEFAULT_SILVER_MERGE_POLICY
        )
        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()
        self.csv_exporter = csv_exporter
        self._write_policy = write_policy or WriteModePolicy()
        self._metrics = metrics
        self._audit = audit
        self._tracing: TracingPort = tracing
        if silver_validator is None:
            from bioetl.infrastructure.validation.pandera_validator import (
                NoOpSilverValidator,
            )

            silver_validator = NoOpSilverValidator()
        self._silver_validator: SilverValidatorPort = silver_validator
        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_silver(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert)."""
        return await self._write_silver_with_tracing(
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
        )

    async def _write_silver_with_tracing(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        partition_cols: list[str] | None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        bronze_refs: list[BronzeWriteResult] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> SilverWriteResult | None:
        started_at, start_perf = datetime.now(UTC), time.perf_counter()
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_silver") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))
            ctx = _SilverWriteExecutionContext(
                table_name=table_name,
                primary_keys=primary_keys,
                schema=schema,
                mode=mode,
                partition_cols=partition_cols,
                on_schema_mismatch=on_schema_mismatch,
                column_order=column_order,
                bronze_refs=bronze_refs,
                key_nullability_rules=key_nullability_rules,
                started_at=started_at,
                start_perf=start_perf,
                span=span,
            )
            return await self._execute_silver_write_pipeline(
                records=records,
                ctx=ctx,
            )

    async def _execute_silver_write_pipeline(
        self,
        *,
        records: list[BronzeRecord],
        ctx: _SilverWriteExecutionContext,
    ) -> SilverWriteResult | None:
        (
            records,
            validated_mode,
            table_path,
            arrow_data,
        ) = await self._prepare_silver_write_payload(
            table_name=ctx.table_name,
            records=records,
            primary_keys=ctx.primary_keys,
            schema=ctx.schema,
            mode=ctx.mode,
            on_schema_mismatch=ctx.on_schema_mismatch,
            column_order=ctx.column_order,
            partition_cols=ctx.partition_cols,
            key_nullability_rules=ctx.key_nullability_rules,
        )
        ctx.span.set_attribute("record_count", len(records))
        await self._dispatch_write_with_domain_errors(
            table_name=ctx.table_name,
            validated_mode=validated_mode,
            table_path=table_path,
            arrow_data=arrow_data,
            primary_keys=ctx.primary_keys,
            partition_cols=ctx.partition_cols,
        )
        return await self._complete_silver_write_pipeline(
            ctx=ctx,
            records=records,
            validated_mode=validated_mode,
            table_name=ctx.table_name,
            table_path=table_path,
            arrow_data=arrow_data,
        )

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        records: list[BronzeRecord],
        validated_mode: SilverWriteMode,
        table_name: str,
        table_path: str,
        arrow_data: pa.Table,
    ) -> SilverWriteResult | None:
        await self._maybe_export_csv(
            table_name=ctx.table_name,
            arrow_data=arrow_data,
            mode=ctx.mode,
            validated_mode=validated_mode,
            primary_keys=ctx.primary_keys,
        )
        await self._maybe_log_silver_audit(
            table_name=ctx.table_name,
            records=records,
            mode=validated_mode,
        )
        return await self._finalize_silver_write_result(
            table_name=table_name,
            records=records,
            table_path=table_path,
            primary_keys=ctx.primary_keys,
            validated_mode=validated_mode,
            bronze_refs=ctx.bronze_refs,
            partition_cols=ctx.partition_cols,
            started_at=ctx.started_at,
            start_perf=ctx.start_perf,
        )

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
    ) -> tuple[list[BronzeRecord], SilverWriteMode, str, pa.Table]:
        records = self._deduplicate_by_primary_keys(records, primary_keys)
        validated_mode = self._validate_write_mode(mode)
        self._enforce_write_policy(validated_mode, table_name)
        self._validate_records(records, table_name, schema)
        self._validate_key_nullability(
            records,
            primary_keys,
            partition_cols,
            key_nullability_rules,
            table_name,
        )
        self._validate_silver_pandera(records, table_name)
        await self._check_schema_drift(table_name, records, on_schema_mismatch)
        table_path = self._resolve_table_path(table_name)
        arrow_data = self._prepare_arrow_data(
            records,
            schema,
            primary_keys,
            column_order=column_order,
        )
        return records, validated_mode, table_path, arrow_data

    async def _dispatch_write_with_domain_errors(
        self,
        *,
        table_name: str,
        validated_mode: SilverWriteMode,
        table_path: str,
        arrow_data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        try:
            await self._dispatch_write(
                validated_mode,
                table_path,
                arrow_data,
                primary_keys,
                partition_cols,
            )
        except (SchemaMismatchError, pa.ArrowTypeError) as exc:
            raise SchemaViolationError(table_name, errors=[str(exc)]) from exc
        except DeltaError as exc:
            if "Merge-conflict" in str(exc):
                raise MergeConflictError(table_name, conflicts=1) from exc
            raise

    async def _maybe_export_csv(
        self,
        *,
        table_name: str,
        arrow_data: pa.Table,
        mode: str,
        validated_mode: SilverWriteMode,
        primary_keys: list[str],
    ) -> None:
        if not self.csv_exporter:
            return
        csv_append = mode != "delete"
        csv_primary_keys = (
            primary_keys if validated_mode == SilverWriteMode.MERGE else None
        )
        await self.csv_exporter.export(
            table_name,
            arrow_data,
            append=csv_append,
            primary_keys=csv_primary_keys,
        )

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None:
        if self._audit and records:
            await self._log_silver_audit(
                table_name=table_name,
                records=records,
                mode=mode,
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
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None:
        dq_metrics = await self._compute_dq_metrics(table_name, records)
        version_after = await self._get_delta_version(table_path)
        completed_at = started_at + timedelta(seconds=time.perf_counter() - start_perf)

        await self._write_silver_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            mode=validated_mode,
            bronze_refs=bronze_refs,
            dq_metrics=dq_metrics,
            partition_by=partition_cols,
            started_at=started_at,
            completed_at=completed_at,
        )
        if version_after is None:
            return None

        from bioetl.domain.value_objects.silver_result import SilverWriteResult

        return SilverWriteResult(
            table_name=table_name,
            table_path=table_path,
            delta_version=version_after,
            record_count=len(records),
        )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files not referenced by the Delta log."""
        return await self._retention_manager.vacuum(
            table_name,
            retention_hours=retention_hours,
            dry_run=dry_run,
        )

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: list[
                               tuple[str, str, Any]  # Any: Delta Lake partition filter values vary
                           ]  # Any: Delta Lake partition filter values vary
                           | None = None,  # Any: Delta Lake partition filter values vary
    ) -> MetaDict:
        """Optimize table layout (compaction)."""
        return await self._retention_manager.optimize(
            table_name,
            target_size=target_size,
            partition_filters=partition_filters,
        )

    async def get_table_info(self, table_name: str) -> MetaDict:
        """Get metadata about a Delta table."""
        return await self._retention_manager.get_table_info(table_name)

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read a previous version of a table."""
        return await self._retention_manager.time_travel(
            table_name,
            version=version,
            timestamp=timestamp,
        )

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Read records from a Silver layer Delta table."""
        return await self.read_table(table_name, columns=columns)
