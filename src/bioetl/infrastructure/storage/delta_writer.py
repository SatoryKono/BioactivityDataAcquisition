"""Silver layer writer (Delta Lake with merge/upsert).

Implements RULES.md §2.1.1 - Silver Layer specifications.

Requirements:
- REQ-DATA-006: Delta Lake format (ACID transactions)
- REQ-DATA-007: Merge/Upsert strategy
- REQ-DATA-008: Time Travel support
- REQ-DELTA-001: Protocol Version (Writer 2, Reader 1)
- REQ-DELTA-002: VACUUM scheduler (7-day retention)
- REQ-DELTA-003: Forensic retention (7-30 days configurable)
- REQ-LINEAGE-001: Records contain _source_batch_id

Architecture:
- Uses deltalake (delta-rs) for Python
- Local filesystem storage
- Supports partitioning for query optimization
- Implements merge/upsert based on primary keys
- ACID guarantees for concurrent writes
- CSV export delegated to CsvExporter (composition)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Literal

import orjson
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
from bioetl.domain.locking import LockContext
from bioetl.domain.medallion import (
    Layer,
    SilverWriteMode,
    WriteMode,
    WriteModePolicy,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.lock_validator import validate_lock_for_write
from bioetl.infrastructure.storage.retention_manager import RetentionManager

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

# Re-export SilverWriteMode for backward compatibility
# Consumers importing from delta_writer will still work
__all__ = ["DeltaWriter", "SilverWriteMode"]


class DeltaWriter:
    """Writer for Silver layer (normalized data in Delta Lake).

    Implements merge/upsert strategy to handle updates and deduplication.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        csv_exporter: CsvExporter | None = None,
        write_policy: WriteModePolicy | None = None,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        tracing: TracingPort | None = None,
        require_lock: bool = True,
        silver_validator: SilverValidatorPort | None = None,
    ) -> None:
        """Initialize Delta writer.

        Args:
            base_path: Base path for Delta tables (local filesystem)
            logger: Structured logger for observability (MUST be injected)
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
            write_policy: Optional WriteModePolicy for medallion layer validation.
                If None, a default WriteModePolicy is created.
            metrics: Optional MetricsPort for recording policy violation metrics.
            audit: Optional AuditPort for write operation traceability.
                  Use NoOpAudit from composition layer if audit disabled.
            tracing: Optional TracingPort for distributed tracing.
                    Use NoOpTracing from composition layer if tracing disabled.
            require_lock: If True, write operations require valid LockContext.
                         Default is True per RULES.md §3.3.
                         Set to False only for testing or non-concurrent scenarios.
            silver_validator: Optional SilverValidatorPort for Pandera validation.
                            Use NoOpSilverValidator if validation is not required.

        Note: LoggerPort is required per RULES.md DI requirements. All dependencies
        MUST be injected through constructor without fallback defaults.
        """
        self.base_path = str(base_path).rstrip("/")
        self.csv_exporter = csv_exporter
        self.logger = logger
        self._write_policy = write_policy or WriteModePolicy()
        self._metrics = metrics
        self._audit = audit
        self._require_lock = require_lock

        # Use NoOpTracing if not provided
        if tracing is None:
            from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
            tracing = NoOpTracing()
        self._tracing: TracingPort = tracing

        # Use NoOpSilverValidator if not provided
        if silver_validator is None:
            from bioetl.infrastructure.validation.pandera_validator import (
                NoOpSilverValidator,
            )
            silver_validator = NoOpSilverValidator()
        self._silver_validator: SilverValidatorPort = silver_validator

        # Delegate retention operations to RetentionManager
        self._retention_manager = RetentionManager(base_path)

    def _prepare_arrow_data(
        self,
        records: list[dict[str, Any]],
        schema: pa.Schema,
        primary_keys: list[str],
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting."""
        schema_fields = set(schema.names)
        string_fields = {
            field.name
            for field in schema
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
        }

        def serialize_value(key: str, value: Any) -> Any:
            """Serialize complex values to JSON strings for PyArrow compatibility.

            Args:
                key: Field name to check against string_fields.
                value: Value to potentially serialize.

            Returns:
                JSON string if value is dict/list and field is string type,
                otherwise the original value unchanged.

            Note:
                Uses OPT_SORT_KEYS for deterministic serialization (§2.8.1).
                Complex objects in Gold layer are flattened; Silver preserves
                JSON for forensic purposes.
            """
            if value is None:
                return None
            if key in string_fields and isinstance(value, (dict, list)):
                # orjson.dumps returns bytes, but PyArrow string columns expect str
                return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
            return value

        filtered_records = [
            {k: serialize_value(k, v) for k, v in rec.items() if k in schema_fields}
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)

        if primary_keys:
            arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])
        return arrow_data

    async def _write_delete(
        self, table_path: str, data: pa.Table, partition_cols: list[str] | None
    ) -> None:
        """Write data in delete mode (replace all existing data)."""
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
        """Write data in append mode."""
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
        """Write data using merge/upsert strategy."""
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
        """Validate and convert write mode string to enum."""
        try:
            return SilverWriteMode(mode)
        except ValueError:
            valid_modes = [m.value for m in SilverWriteMode]
            raise ValueError(
                f"Invalid Silver write mode '{mode}'. Allowed: {valid_modes}"
            ) from None

    def _validate_lock_held(
        self,
        table_name: str,
        lock_context: LockContext | None,
        expected_owner_id: RunID | None = None,
    ) -> None:
        """Validate that lock is held before write operation.

        Delegates to centralized lock_validator module.
        Implements RULES.md §3.3 - Writers MUST verify lock held.
        """
        validate_lock_for_write(
            table_name=table_name,
            lock_context=lock_context,
            logger=self.logger,
            operation="write_silver",
            require_lock=self._require_lock,
            expected_owner_id=expected_owner_id,
        )

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Map SilverWriteMode to WriteMode for policy validation.

        Args:
            mode: The SilverWriteMode to convert.

        Returns:
            The corresponding WriteMode for policy validation.

        Note:
            SilverWriteMode.DELETE maps to WriteMode.OVERWRITE because
            the delete operation replaces all existing data.
        """
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
        """Enforce write mode policy for Silver layer.

        Args:
            mode: The validated SilverWriteMode.
            table_name: Target table name for logging/metrics context.

        Raises:
            PolicyViolationError: If mode is not allowed for Silver layer.
        """
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
        """Validate records have required metadata fields."""
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
        """Validate records using Pandera schema before writing to Silver.

        Args:
            records: List of record dictionaries to validate.
            table_name: Target table name for error context.

        Raises:
            SchemaViolationError: If Pandera validation fails.
        """
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
        """Dispatch write to appropriate method based on mode."""
        if validated_mode == SilverWriteMode.DELETE:
            await self._write_delete(table_path, arrow_data, partition_cols)
        elif validated_mode == SilverWriteMode.APPEND:
            await self._write_append(table_path, arrow_data, partition_cols)
        else:  # SilverWriteMode.MERGE
            await self._write_merge(
                table_path, arrow_data, primary_keys, partition_cols
            )

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get existing table schema if table exists.

        Args:
            table_name: Target table name

        Returns:
            PyArrow schema if table exists, None otherwise
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return dt.schema().to_arrow()
        except DeltaTableNotFoundError:
            return None

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check for schema drift and handle according to policy.

        Args:
            table_name: Target table name
            records: List of records to write
            on_schema_mismatch: How to handle schema drift

        Raises:
            SchemaEvolutionError: If on_schema_mismatch='error' and drift detected
        """
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
        # "evolve" and "ignore" proceed without error
        # "evolve" will let Delta Lake handle schema evolution via schema_mode
        # "ignore" will filter records to match existing schema

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        lock_context: LockContext | None = None,
        **kwargs: Any,
    ) -> None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert).

        Args:
            table_name: Target table name
            records: List of records to write
            primary_keys: Primary key columns for merge
            schema: PyArrow schema for the table
            mode: Write mode - 'merge', 'append', or 'delete'
            partition_cols: Optional partition columns
            on_schema_mismatch: How to handle schema drift:
                - 'error': Raise SchemaEvolutionError (default)
                - 'evolve': Allow schema evolution (add new columns)
                - 'ignore': Proceed without changes (filter to existing schema)
            lock_context: Lock context from LockManager. Required unless
                         require_lock=False was passed to constructor (RULES.md §3.3).
            **kwargs: Additional arguments for compatibility (ignored).

        Raises:
            ValueError: If mode is invalid or records are missing required fields
            PolicyViolationError: If mode is not allowed for Silver layer
            SchemaEvolutionError: If schema drift detected and on_schema_mismatch='error'
            SchemaViolationError: If Pandera validation fails
            LockNotHeldError: If lock_context is None or invalid (when require_lock=True)
        """
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_silver") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))

            # Extract expected owner_id from records for fencing token validation
            expected_owner_id: RunID | None = None
            if records:
                run_id_str = records[0].get("_run_id")
                if run_id_str:
                    from uuid import UUID
                    try:
                        expected_owner_id = RunID(UUID(run_id_str))
                    except (ValueError, TypeError):
                        # Invalid run_id format, skip owner validation
                        self.logger.warning(
                            "Could not parse _run_id for owner validation",
                            table=table_name,
                            run_id=run_id_str,
                        )

            # Validate lock is held before any write operation (RULES.md §3.3)
            self._validate_lock_held(table_name, lock_context, expected_owner_id)

            validated_mode = self._validate_write_mode(mode)

            # Enforce medallion layer write mode policy (Silver allows only merge/append)
            self._enforce_write_policy(validated_mode, table_name)

            self._validate_records(records, table_name, schema)

            # Validate records using Pandera schema (if configured)
            self._validate_silver_pandera(records, table_name)

            # Check for schema drift before writing
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
                await self.csv_exporter.export(table_name, arrow_data, append=csv_append)

            # Log audit entry for write operation
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
        """Log audit entry for Silver write operation.

        Args:
            table_name: Target table name
            records: List of records written
            mode: Write mode used
        """
        # Skip audit if no audit port configured
        if self._audit is None:
            return

        from datetime import datetime
        from uuid import UUID

        from bioetl.domain.types import RunID

        # Extract run_id and timestamp from first record
        first_record = records[0]
        run_id_str = first_record.get("_run_id", "")
        ingestion_ts_str = first_record.get("_ingestion_ts")

        # Parse run_id (UUID string)
        try:
            run_id = RunID(UUID(run_id_str))
        except (ValueError, TypeError):
            # If run_id is not a valid UUID, skip audit logging
            self.logger.warning(
                "audit_skipped_invalid_run_id",
                table=table_name,
                run_id=run_id_str,
            )
            return

        # Parse timestamp
        if isinstance(ingestion_ts_str, str):
            timestamp = datetime.fromisoformat(ingestion_ts_str)
        elif isinstance(ingestion_ts_str, datetime):
            timestamp = ingestion_ts_str
        else:
            from datetime import UTC

            timestamp = datetime.now(UTC)

        # Map SilverWriteMode to AuditOperation
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
        """Merge records into existing Delta table."""
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

    def get_table_path(self, table_name: str) -> Path:
        """Get the filesystem path for a table.

        Args:
            table_name: Table name (e.g., 'chembl.activity')

        Returns:
            Path to the table directory.

        """
        from pathlib import Path

        return Path(self.base_path) / table_name.replace(".", "/")

    def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
        """Clear Delta table(s) at the start of a pipeline run.

        Args:
            table_name: If provided, only clear this table.
                       If None, clear all tables in base_path.
            dry_run: If True, only count what would be deleted.

        Returns:
            Number of tables cleared (or would be cleared).

        """
        import shutil
        from pathlib import Path

        base = Path(self.base_path)
        if not base.exists():
            return 0

        cleared = 0
        if table_name:
            # Clear specific table
            table_path = self.get_table_path(table_name)
            if table_path.exists():
                if not dry_run:
                    shutil.rmtree(table_path)
                cleared = 1
        else:
            # Clear all Delta tables (directories with _delta_log)
            for item in base.iterdir():
                if item.is_dir() and (item / "_delta_log").exists():
                    if not dry_run:
                        shutil.rmtree(item)
                    cleared += 1

        return cleared

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files that are no longer referenced by the Delta log.

        Delegates to RetentionManager for maintenance operations.

        Args:
            table_name: Table name.
            retention_hours: Hours of retention.
            dry_run: If True, only list files to be deleted.

        Returns:
            List of files deleted (or to be deleted).
        """
        return await self._retention_manager.vacuum(
            table_name, retention_hours=retention_hours, dry_run=dry_run
        )

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Optimize table layout (compaction).

        Delegates to RetentionManager for maintenance operations.

        Args:
            table_name: Table name.
            target_size: Target file size in bytes (currently unused, reserved for future).
            partition_filters: Optional filters to limit optimization to specific partitions.

        Returns:
            Optimization metrics.
        """
        return await self._retention_manager.optimize(
            table_name, target_size=target_size, partition_filters=partition_filters
        )

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get metadata about a Delta table.

        Delegates to RetentionManager for maintenance operations.

        Args:
            table_name: Table name.

        Returns:
            Dictionary with table metadata (version, files, history).
        """
        return await self._retention_manager.get_table_info(table_name)

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read a previous version of the table.

        Delegates to RetentionManager for maintenance operations.

        Args:
            table_name: Table name.
            version: Version number.
            timestamp: Timestamp string.

        Returns:
            PyArrow table or equivalent of the snapshot.
        """
        return await self._retention_manager.time_travel(
            table_name, version=version, timestamp=timestamp
        )
