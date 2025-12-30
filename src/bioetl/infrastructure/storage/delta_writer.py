"""Silver layer writer (Delta Lake with merge/upsert).

Implements RULES.md §2.1.1 - Silver Layer specifications.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import (
    MergeConflictError,
    PolicyViolationError,
    SchemaEvolutionError,
    SchemaViolationError,
)
from bioetl.domain.medallion import (
    Layer,
    SilverWriteMode,
    WriteMode,
    WriteModePolicy,
)
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter

from bioetl.domain.ports.audit import AuditEntry, AuditLayer, AuditOperation

__all__ = ["DeltaWriter", "SilverWriteMode"]


class DeltaWriter(BaseDeltaWriter):
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
    ) -> None:
        super().__init__(base_path, logger)
        if tracing is None:
            from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
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

    async def _write_delete(
        self, table_path: str, data: pa.Table, partition_cols: list[str] | None
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="overwrite",
                partition_by=partition_cols,
                schema_mode="overwrite",
            ),
        )

    async def _write_append(
        self, table_path: str, data: pa.Table, partition_cols: list[str] | None
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="append",
                partition_by=partition_cols,
            ),
        )

    async def _write_merge(
        self,
        table_path: str,
        data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            await self._merge_records(dt, data, primary_keys)
        except DeltaTableNotFoundError:
            await self._write_append(table_path, data, partition_cols)

    def _validate_write_mode(self, mode: str) -> SilverWriteMode:
        try:
            return SilverWriteMode(mode)
        except ValueError:
            valid_modes = [m.value for m in SilverWriteMode]
            raise ValueError(
                f"Invalid Silver write mode '{mode}'. Allowed: {valid_modes}"
            ) from None

    def _deduplicate_by_primary_keys(
        self, records: list[dict[str, Any]], primary_keys: list[str]
    ) -> list[dict[str, Any]]:
        if not primary_keys or not records:
            return records

        first_record = records[0]
        missing_keys = [pk for pk in primary_keys if pk not in first_record]

        if missing_keys:
            self.logger.warning(
                "Cannot deduplicate records: missing primary keys",
                missing_keys=missing_keys,
                available_keys=list(first_record.keys())
            )
            return records

        unique_records: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in records:
            key = tuple(record.get(pk) for pk in primary_keys)
            unique_records[key] = record
        return list(unique_records.values())

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        mapping = {
            SilverWriteMode.MERGE: WriteMode.MERGE,
            SilverWriteMode.APPEND: WriteMode.APPEND,
            SilverWriteMode.DELETE: WriteMode.OVERWRITE,
        }
        return mapping[mode]

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        policy_mode = self._to_policy_write_mode(mode)
        try:
            self._write_policy.validate(Layer.SILVER, policy_mode)
        except PolicyViolationError:
            self.logger.error(
                "Write mode policy violation",
                layer="silver",
                mode=mode.value,
                policy_mode=policy_mode.value,
                table=table_name,
            )
            if self._metrics:
                self._metrics.increment_counter(
                    "policy_violations_total",
                    1,
                    {"layer": "silver", "mode": policy_mode.value},
                )
            raise

    def _validate_records(
        self, records: list[dict[str, Any]], table_name: str, schema: pa.Schema
    ) -> None:
        if not records:
            raise ValueError("No records to write")

        required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        if missing_fields := required_fields - set(records[0].keys()):
            raise ValueError(
                f"Records missing required metadata fields: {missing_fields}"
            )

        if self.logger:
            keys = set(records[0].keys())
            optional_missing = [k for k in schema.names if k not in keys]
            if optional_missing:
                self.logger.debug(
                    "Optional fields missing in batch",
                    table=table_name,
                    missing=optional_missing,
                )

    def _validate_silver_pandera(
        self, records: list[dict[str, Any]], table_name: str
    ) -> None:
        result = self._silver_validator.validate(records)
        if not result.valid:
            self.logger.error(
                "Silver Pandera validation failed",
                table=table_name,
                errors=result.errors,
            )
            if self._metrics:
                self._metrics.increment_counter(
                    "silver_validation_failures_total",
                    1,
                    {"table": table_name},
                )
            raise SchemaViolationError(table_name, result.errors)

    async def _dispatch_write(
        self,
        validated_mode: SilverWriteMode,
        table_path: str,
        arrow_data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        if validated_mode == SilverWriteMode.DELETE:
            await self._write_delete(table_path, arrow_data, partition_cols)
        elif validated_mode == SilverWriteMode.APPEND:
            await self._write_append(table_path, arrow_data, partition_cols)
        else:
            await self._write_merge(
                table_path, arrow_data, primary_keys, partition_cols
            )

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        existing_schema = await self._get_table_schema(table_name)
        if existing_schema is None or not records:
            return

        incoming_fields = set(records[0].keys())
        existing_fields = set(existing_schema.names)

        new_fields = incoming_fields - existing_fields
        removed_fields = existing_fields - incoming_fields

        if not new_fields and not removed_fields:
            return

        self.logger.warning(
            "Schema drift detected",
            table=table_name,
            new_fields=sorted(new_fields) if new_fields else None,
            removed_fields=sorted(removed_fields) if removed_fields else None,
            action=on_schema_mismatch,
        )

        if on_schema_mismatch == "error":
            raise SchemaEvolutionError(
                table=table_name,
                new_fields=new_fields,
                removed_fields=removed_fields,
            )

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
    ) -> None:
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
            self._validate_silver_pandera(records, table_name)
            await self._check_schema_drift(table_name, records, on_schema_mismatch)

            table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
            arrow_data = self._prepare_arrow_data(records, schema, primary_keys)

            try:
                await self._dispatch_write(
                    validated_mode, table_path, arrow_data, primary_keys, partition_cols
                )
            except (SchemaMismatchError, ArrowTypeError) as e:
                raise SchemaViolationError(table_name, errors=[str(e)]) from e
            except DeltaError as e:
                if "Merge-conflict" in str(e):
                    raise MergeConflictError(table_name, conflicts=1) from e
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

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: SilverWriteMode,
    ) -> None:
        if self._audit is None:
            return

        from datetime import datetime
        from uuid import UUID

        from bioetl.domain.types import RunID

        first_record = records[0]
        run_id_str = first_record.get("_run_id", "")
        ingestion_ts_str = first_record.get("_ingestion_ts")

        try:
            run_id = RunID(UUID(run_id_str))
        except (ValueError, TypeError):
            self.logger.warning(
                "audit_skipped_invalid_run_id",
                table=table_name,
                run_id=run_id_str,
            )
            return

        if isinstance(ingestion_ts_str, str):
            timestamp = datetime.fromisoformat(ingestion_ts_str)
        elif isinstance(ingestion_ts_str, datetime):
            timestamp = ingestion_ts_str
        else:
            raise ValueError("_ingestion_ts is required for audit logging")

        operation_map = {
            SilverWriteMode.MERGE: AuditOperation.MERGE,
            SilverWriteMode.APPEND: AuditOperation.APPEND,
            SilverWriteMode.DELETE: AuditOperation.DELETE,
        }
        operation = operation_map[mode]

        audit_entry = AuditEntry(
            run_id=run_id,
            timestamp=timestamp,
            layer=AuditLayer.SILVER,
            table_name=table_name,
            operation=operation,
            records_count=len(records),
            metadata={
                "run_type": first_record.get("_run_type", ""),
                "source_batch_id": first_record.get("_source_batch_id", ""),
            },
        )
        await self._audit.log_write(audit_entry)

    async def _merge_records(
        self,
        dt: DeltaTable,
        records: pa.Table | pa.RecordBatchReader,
        primary_keys: list[str],
    ) -> None:
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: (
                dt.merge(
                    source=records,
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update_all(
                    predicate=(
                        "CASE "
                        "WHEN source._run_type = 'rebuild' THEN 3 "
                        "WHEN source._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END >= "
                        "CASE "
                        "WHEN target._run_type = 'rebuild' THEN 3 "
                        "WHEN target._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END"
                    )
                )
                .when_not_matched_insert_all()
                .execute()
            ),
        )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        return await self._retention_manager.vacuum(
            table_name, retention_hours=retention_hours, dry_run=dry_run
        )

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        return await self._retention_manager.optimize(
            table_name, target_size=target_size, partition_filters=partition_filters
        )

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        return await self._retention_manager.get_table_info(table_name)

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        return await self._retention_manager.time_travel(
            table_name, version=version, timestamp=timestamp
        )
