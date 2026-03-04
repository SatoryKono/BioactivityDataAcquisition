"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError

from bioetl.domain.exceptions import MergeConflictError, SchemaViolationError
from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord, MetaDict
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,
)
from bioetl.infrastructure.storage.silver_writer_arrow_mixin import (
    SilverWriterArrowMixin,
)
from bioetl.infrastructure.storage.silver_writer_delta_mixin import (
    SilverWriterDeltaMixin,
)
from bioetl.infrastructure.storage.silver_writer_metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver_writer_validation_mixin import (
    SilverWriterValidationMixin,
)

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


class SilverWriter(  # type: ignore[misc]  # Callable vs async-def in MRO
    SilverWriterArrowMixin,
    SilverWriterValidationMixin,
    SilverWriterDeltaMixin,
    SilverWriterMetadataMixin,
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
    ) -> None:
        """Initialize Silver writer."""
        super().__init__(base_path, logger, flat_structure=flat_structure)
        self._dq_calculator = dq_calculator or DQMetricsCalculator()

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
        started_at, start_perf = datetime.now(UTC), time.perf_counter()
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_silver") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))

            records = self._deduplicate_by_primary_keys(records, primary_keys)
            span.set_attribute("record_count", len(records))

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

            if self.csv_exporter:
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

            if self._audit and records:
                await self._log_silver_audit(
                    table_name=table_name,
                    records=records,
                    mode=validated_mode,
                )

            dq_metrics = await self._compute_dq_metrics(table_name, records)
            version_after = await self._get_delta_version(table_path)
            completed_at = started_at + timedelta(
                seconds=time.perf_counter() - start_perf
            )

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

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema."""
        from bioetl.domain.schemas.column_order import canonical_column_order

        if not records:
            self.logger.warning(
                "No records to write for merged Silver",
                table_name=table_name,
            )
            return

        arrow_table = pa.Table.from_pylist(records)
        arrow_table = coerce_null_types_for_delta(arrow_table)
        schema = arrow_table.schema

        if not preserve_column_order:
            ordered_columns = canonical_column_order(list(arrow_table.column_names))
            arrow_table = arrow_table.select(ordered_columns)

        if primary_keys:
            valid_keys = [key for key in primary_keys if key in schema.names]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(key, "ascending") for key in valid_keys]
                )

        table_path = self._resolve_table_path(table_name)

        self.logger.info(
            "Writing merged Silver records",
            table_name=table_name,
            path=table_path,
            records=len(records),
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_path,
                arrow_table,
                mode="overwrite",
                schema_mode="overwrite",
            ),
        )

        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_table,
                append=False,
            )

        await self._write_silver_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys or [],
            run_id=run_id,
            sources_used=sources_used,
        )
