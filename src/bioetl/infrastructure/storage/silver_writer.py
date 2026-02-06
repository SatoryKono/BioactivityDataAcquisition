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

Note:
    This class was renamed from DeltaWriter to SilverWriter to follow
    the Medallion layer naming convention (BronzeWriter, SilverWriter, GoldWriter).
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
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
from bioetl.domain.medallion import Layer, SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    from bioetl.domain.value_objects.dq_metrics import (
        BatchDQMetrics,
        SchemaDriftInfo,
    )
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.export.csv_exporter import CsvExporter

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation

# Re-export SilverWriteMode for backward compatibility
# Consumers importing from silver_writer will still work
__all__ = ["SilverWriteMode", "SilverWriter"]


class SilverWriter(BaseDeltaWriter):
    """Writer for Silver layer (normalized data in Delta Lake).

    Inherits from BaseDeltaWriter for common Delta Lake operations
    (get_table_path, clear, _get_table_schema).

    Implements merge/upsert strategy to handle updates and deduplication.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

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
    ) -> None:
        """Initialize Silver writer.

        Args:
            base_path: Base path for Delta tables (local filesystem)
            logger: Structured logger for observability (MUST be injected)
            tracing: TracingPort for distributed tracing. Use NoOpTracing from
                    composition layer if tracing is disabled. If None, NoOpTracing
                    is used automatically (for test convenience).
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
            write_policy: Optional WriteModePolicy for medallion layer validation.
                If None, a default WriteModePolicy is created.
            metrics: Optional MetricsPort for recording policy violation metrics.
            audit: Optional AuditPort for write operation traceability.
                  Use NoOpAudit from composition layer if audit disabled.
            silver_validator: Optional SilverValidatorPort for Pandera validation.
                            Use NoOpSilverValidator if validation is not required.
            metadata_writer: Optional MetadataWriterPort for writing _metadata.yaml
                           sidecar files. Use NoOpMetadataWriter if disabled.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation. If provided, uses coordinator
                                instead of local _write_silver_metadata() logic.
                                Ensures consistent run_id across layers.
            transform_version: Optional semver version of transform (e.g., '1.0.0')
                             for lineage tracking in metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            flat_structure: If True, Delta data written directly to base_path
                          without table_name subdirectory.

        Note:
            LoggerPort is required per RULES.md DI requirements.
            Lock validation is now performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
        """
        # Initialize base class (sets base_path, logger, _retention_manager, _flat_structure)
        super().__init__(base_path, logger, flat_structure=flat_structure)

        # Use NoOpTracing if not provided (test convenience, production uses composition)
        if tracing is None:
            from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

            tracing = NoOpTracing()

        self.csv_exporter = csv_exporter
        self._write_policy = write_policy or WriteModePolicy()
        self._metrics = metrics
        self._audit = audit
        self._tracing: TracingPort = tracing

        # Use NoOpSilverValidator if not provided (validation is optional)
        if silver_validator is None:
            from bioetl.infrastructure.validation.pandera_validator import (
                NoOpSilverValidator,
            )

            silver_validator = NoOpSilverValidator()
        self._silver_validator: SilverValidatorPort = silver_validator

        # Use NoOpMetadataWriter if not provided (metadata is optional)
        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

        # Transform version tracking for lineage metadata
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    def _prepare_arrow_data(
        self,
        records: list[dict[str, Any]],
        schema: pa.Schema,
        primary_keys: list[str],
        column_order: list[str] | None = None,
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting."""
        from bioetl.domain.schemas.column_order import canonical_column_order

        # schema_fields is no longer needed as we iterate over schema.names directly
        schema_names = schema.names
        string_fields = {
            field.name
            for field in schema
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
        }

        filtered_records = [
            {
                k: (
                    # Uses OPT_SORT_KEYS for deterministic serialization (§2.8.1).
                    # Complex objects in Gold layer are flattened; Silver preserves
                    # JSON for forensic purposes.
                    orjson.dumps(v, option=orjson.OPT_SORT_KEYS).decode("utf-8")
                    if k in string_fields and isinstance(v, (dict, list))
                    else v
                )
                for k in schema_names
                if (v := rec.get(k)) is not None
            }
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)

        if column_order:
            ordered_columns = [c for c in column_order if c in arrow_data.column_names]
            remaining = [c for c in arrow_data.column_names if c not in ordered_columns]
            arrow_data = arrow_data.select(ordered_columns + remaining)
        else:
            # Enforce canonical column order (ADR-014, RULES.md §2.4)
            ordered_columns = canonical_column_order(list(arrow_data.column_names))
            arrow_data = arrow_data.select(ordered_columns)

        # Sort rows by primary keys for deterministic writes
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

    def _deduplicate_by_primary_keys(
        self, records: list[dict[str, Any]], primary_keys: list[str]
    ) -> list[dict[str, Any]]:
        """Deduplicate records based on primary keys to prevent duplicates in batch."""
        if not primary_keys or not records:
            return records
        unique_records: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in records:
            key = tuple(record.get(pk) for pk in primary_keys)
            unique_records[key] = record
        return list(unique_records.values())

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

    # NOTE: _get_table_schema() is inherited from BaseDeltaWriter

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

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[dict[str, Any]],
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing table and incoming records.

        Non-raising version used for DQ metrics computation.

        Args:
            table_name: Target table name.
            records: List of records to check.

        Returns:
            SchemaDriftInfo if drift detected, None otherwise.
        """
        from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo

        existing_schema = await self._get_table_schema(table_name)
        if existing_schema is None or not records:
            return None

        incoming_fields = set(records[0].keys())
        existing_fields = set(existing_schema.names)

        new_fields = incoming_fields - existing_fields
        missing_fields = existing_fields - incoming_fields

        if not new_fields and not missing_fields:
            return None

        # Determine drift severity
        # Critical: missing required fields (starts with no underscore = business field)
        critical_missing = [f for f in missing_fields if not f.startswith("_")]
        if critical_missing:
            status = "critical"
        elif len(new_fields) > 3:
            status = "warn"
        else:
            status = "info"

        return SchemaDriftInfo(
            status=status,
            new_fields=tuple(sorted(new_fields)),
            missing_fields=tuple(sorted(missing_fields)),
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
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
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
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Raises:
            ValueError: If mode is invalid or records are missing required fields
            PolicyViolationError: If mode is not allowed for Silver layer
            SchemaEvolutionError: If schema drift detected and on_schema_mismatch='error'
            SchemaViolationError: If Pandera validation fails

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        started_at, start_perf = datetime.now(UTC), time.perf_counter()
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_silver") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))

            records = self._deduplicate_by_primary_keys(records, primary_keys)
            span.set_attribute("record_count", len(records))

            validated_mode = self._validate_write_mode(mode)

            # Enforce medallion layer write mode policy (Silver allows only merge/append)
            self._enforce_write_policy(validated_mode, table_name)

            self._validate_records(records, table_name, schema)

            # Validate records using Pandera schema (if configured)
            self._validate_silver_pandera(records, table_name)

            # Check for schema drift before writing
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
                # Pass primary_keys to CSV exporter for deduplication if mode is merge
                csv_primary_keys = (
                    primary_keys if validated_mode == SilverWriteMode.MERGE else None
                )
                await self.csv_exporter.export(
                    table_name,
                    arrow_data,
                    append=csv_append,
                    primary_keys=csv_primary_keys,
                )

            # Log audit entry for write operation
            if self._audit and records:
                await self._log_silver_audit(
                    table_name=table_name,
                    records=records,
                    mode=validated_mode,
                )

            # Compute DQ metrics for metadata (REQ-DQ-001)
            dq_metrics = await self._compute_dq_metrics(table_name, records)

            # Get Delta version after write for lineage tracking (REQ-LINEAGE-002)
            version_after = await self._get_delta_version(table_path)
            # Calculate completed_at (ADR-014: deterministic from start + duration)
            completed_at = started_at + timedelta(
                seconds=time.perf_counter() - start_perf
            )
            # Write metadata sidecar file if configured
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

            # Return SilverWriteResult for Gold lineage tracking (REQ-LINEAGE-002)
            if version_after is not None:
                from bioetl.domain.value_objects.silver_result import SilverWriteResult

                return SilverWriteResult(
                    table_name=table_name,
                    table_path=table_path,
                    delta_version=version_after,
                    record_count=len(records),
                )
            return None

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        quarantined_count: int = 0,
    ) -> BatchDQMetrics:
        """Compute DQ metrics using centralized calculator.

        Args:
            table_name: Target table name for schema drift detection.
            records: List of records to analyze.
            quarantined_count: Number of quarantined records.

        Returns:
            BatchDQMetrics with computed column stats and schema drift info.
        """
        from bioetl.domain.services.dq_metrics_calculator import (
            DQMetricsCalculator,
            DQMetricsInput,
        )

        # Get existing schema for drift detection
        existing_schema = await self._get_table_schema(table_name)
        existing_fields: set[str] | None = None
        if existing_schema is not None:
            existing_fields = set(existing_schema.names)

        calculator = DQMetricsCalculator()
        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
            quarantined_count=quarantined_count,
        )

        return calculator.calculate(input_data)

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

        # Parse timestamp (ensure UTC-aware for consistency)
        from datetime import UTC

        if isinstance(ingestion_ts_str, str):
            timestamp = datetime.fromisoformat(ingestion_ts_str)
        elif isinstance(ingestion_ts_str, datetime):
            timestamp = ingestion_ts_str
        else:
            timestamp = datetime.now(UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

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

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version.

        Args:
            table_path: Full path to the Delta table.

        Returns:
            Current version number, or None if table doesn't exist.
        """
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            version: int = dt.version()
            return version
        except DeltaTableNotFoundError:
            return None

    async def _write_silver_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None = None,
        dq_metrics: BatchDQMetrics | None = None,
        dq_report_path: str | None = None,
        partition_by: list[str] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Write Silver layer metadata sidecar file.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name (used for flat_structure file naming).
            records: List of records written.
            primary_keys: Primary key columns used.
            mode: Write mode used (merge, append, delete).
            bronze_refs: Optional BronzeWriteResult list for lineage (REQ-LINEAGE-001).
            dq_metrics: Optional BatchDQMetrics for DQ summary (REQ-DQ-001).
            dq_report_path: Optional path to generated DQ report.
            partition_by: Partition columns used for the Delta table.
            started_at: UTC timestamp when Silver write started.
            completed_at: UTC timestamp when Silver write completed.
        """
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is None:
            self.logger.warning(
                "silver_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return

        from bioetl.domain.ports import SilverMetadataInput

        version_after = await self._get_delta_version(table_path)

        silver_input = SilverMetadataInput(
            table_path=table_path,
            records=records,
            primary_keys=primary_keys,
            mode=mode,
            bronze_refs=bronze_refs,
            dq_metrics=dq_metrics,
            version_after=version_after,
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            dq_report_path=dq_report_path,
            partition_by=partition_by,
            started_at=started_at,
            completed_at=completed_at,
        )
        metadata = self._metadata_coordinator.create_silver_metadata(silver_input)
        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

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

    # NOTE: get_table_path() and clear() are inherited from BaseDeltaWriter

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

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        return await self.read_table(table_name, columns=columns)

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined.
        Schema is inferred from the records using PyArrow type inference.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical_column_order()
                and preserve the column order from records (e.g. semantic
                ordering applied by ColumnOrderer in composite pipelines).
        """
        from bioetl.domain.schemas.column_order import canonical_column_order

        if not records:
            self.logger.warning(
                "No records to write for merged Silver",
                table_name=table_name,
            )
            return

        # Infer schema from records using PyArrow
        arrow_table = pa.Table.from_pylist(records)

        # Coerce Null-typed columns for Delta Lake compatibility
        arrow_table = coerce_null_types_for_delta(arrow_table)
        schema = arrow_table.schema

        # Apply canonical column order unless caller already ordered columns
        # (e.g. ColumnOrderer in composite pipelines applies semantic ordering)
        if not preserve_column_order:
            ordered_columns = canonical_column_order(list(arrow_table.column_names))
            arrow_table = arrow_table.select(ordered_columns)

        # Sort by primary keys if provided for deterministic writes
        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in schema.names]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(pk, "ascending") for pk in valid_keys]
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

        # Export to CSV if configured (composite pipelines use overwrite mode)
        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_table,
                append=False,  # Merged data replaces existing CSV
            )

        # Write metadata sidecar for composite merged data
        await self._write_silver_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys or [],
            run_id=run_id,
            sources_used=sources_used,
        )

    async def _write_silver_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write Silver layer metadata sidecar for merged composite data.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name (used for filename generation).
            records: List of records written.
            primary_keys: Primary key columns used.
            run_id: Composite run ID for tracking.
            sources_used: List of source pipelines (e.g., ['seed', 'crossref', 'openalex']).
        """
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import (
            SilverMetadataBuilder,
            _parse_table_name,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is None:
            self.logger.debug(
                "silver_merged_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return

        # Get Delta version after write
        version_after = await self._get_delta_version(table_path)

        # Build metadata using the extracted builder
        builder = SilverMetadataBuilder(
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
        )
        metadata = builder.build_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            version_after=version_after,
        )

        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )
