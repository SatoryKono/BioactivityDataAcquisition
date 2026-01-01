"""Batch writing to Bronze, Silver, and Gold layers.

Handles all storage operations with proper metadata enrichment.
Extracted from RecordProcessor for single responsibility (SRP).

Safety Guard (RULES.md §4.6):
    Lock validation is performed at this Application layer BEFORE any write
    operation. This ensures Infrastructure layer (Writers) remain pure I/O
    adapters without knowledge of locking mechanisms.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast

import orjson

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.locking import LockNotHeldError

if TYPE_CHECKING:
    from typing import Any as SpanType

    from bioetl.application.core.batch_metrics import BatchMetricsRecorder
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, StoragePort, TracingPort
    from bioetl.domain.types import BatchID


class BatchWriter:
    """Writes records to Bronze, Silver, and Gold layers.

    Handles:
    - Bronze: JSONL serialization with deterministic ordering
    - Silver: Metadata enrichment (_run_id, _run_type, etc.)
    - Gold: Schema validation and column filtering

    Safety Guard:
        Lock validation is performed BEFORE each write operation via
        the lock_validator callback. This implements RULES.md §4.6.
    """

    def __init__(
        self,
        storage: StoragePort,
        context: PipelineContext,
        config: RecordProcessorConfig,
        gold_validator: GoldValidatorPort,
        error_classifier: ErrorClassifier,
        batch_metrics: BatchMetricsRecorder,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        """Initialize batch writer.

        Args:
            storage: Storage port for writing to all layers.
            context: Pipeline execution context.
            config: Record processor configuration.
            gold_validator: Validator for Gold layer records.
            error_classifier: Service for error classification.
            batch_metrics: Metrics recorder for batch processing.
            tracer: Optional tracing port for distributed tracing.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                If None, lock validation is skipped (for tests).

        """
        self._storage = storage
        self._context = context
        self._config = config
        self._gold_validator = gold_validator
        self._error_classifier = error_classifier
        self._batch_metrics = batch_metrics
        self._tracer = tracer
        self._lock_validator = lock_validator

        # Convenience properties
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config

        # Performance Optimization: Cache gold schema columns to avoid repeated
        # schema introspection and conversion overhead in the hot loop (write_gold).
        # This prevents calling to_schema() for every batch.
        self._gold_schema_columns = self._get_schema_columns(config.gold_schema)

    async def _validate_lock(self, operation: str) -> None:
        """Validate lock ownership before write operation (Safety Guard §4.6).

        Args:
            operation: Name of the operation for error messages.

        Raises:
            LockNotHeldError: If lock is no longer held.
        """
        if self._lock_validator is None:
            # Lock validation disabled (e.g., for tests)
            return

        if not await self._lock_validator():
            table_name = f"{self._provider}_{self._entity_type}"
            self._context.logger.error(
                "Lock lost before write",
                operation=operation,
                table=table_name,
                run_id=str(self._context.run_id),
            )
            raise LockNotHeldError(operation, f"lock:{table_name}")

    def _start_span(
        self, name: str, layer: str, record_count: int, batch_id: BatchID | None = None
    ) -> SpanType | None:
        """Start a tracing span for a write operation.

        Args:
            name: Span name (e.g., "write_bronze").
            layer: Layer name (bronze, silver, gold).
            record_count: Number of records being written.
            batch_id: Optional batch identifier.

        Returns:
            Span context manager or None if tracer is not available.
        """
        if not self._tracer:
            return None

        attrs: dict[str, Any] = {
            "bioetl.layer": layer,
            "bioetl.record_count": record_count,
            "bioetl.provider": self._provider,
            "bioetl.entity_type": self._entity_type,
        }
        if batch_id:
            attrs["bioetl.batch_id"] = str(batch_id)

        span = self._tracer.get_tracer("bioetl.batch_writer").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _end_span(self, span: SpanType | None, error: Exception | None = None) -> None:
        """End a tracing span.

        Args:
            span: Span to end (may be None if tracer was not available).
            error: Optional exception to record on the span.
        """
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    async def write_bronze(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        """Write records to Bronze layer.

        Serializes records to JSON with deterministic key ordering,
        sorts by content for reproducibility.

        Args:
            records: Raw records to write.
            batch_id: Identifier for the current batch.
            ingestion_ts: Ingestion timestamp from context.

        Raises:
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_bronze")

        span = self._start_span("write_bronze", "bronze", len(records), batch_id)

        try:
            # Serialize with deterministic key ordering
            # orjson returns bytes
            json_bytes_list = [
                orjson.dumps(r, option=orjson.OPT_SORT_KEYS) for r in records
            ]

            # Sort bytes for deterministic file content
            json_bytes_list.sort()

            # Create generator for bytes with newlines
            record_bytes = (b + b"\n" for b in json_bytes_list)

            await self._storage.write_bronze(
                records=record_bytes,
                provider=self._provider,
                entity=self._entity_type,
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=self._context.run_id,
                run_type=self._context.run_type,
                ingestion_ts=ingestion_ts,
            )
            self._end_span(span)
        except Exception as e:
            self._end_span(span, e)
            raise

    async def write_silver(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        """Write records to Silver layer with metadata.

        Enriches records with _run_id, _run_type, _source_batch_id, _ingestion_ts.

        Args:
            records: Transformed Silver records.
            batch_id: Identifier for the source batch.
            ingestion_ts: Ingestion timestamp from context.

        Raises:
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_silver")

        span = self._start_span("write_silver", "silver", len(records), batch_id)

        try:
            # Records already have lineage fields from BaseTransformer.entity_to_silver_record
            # But we need to ensure they are present and correct, especially source_batch_id
            # which might be None in entity if not passed during creation.

            # We update _source_batch_id here as it is batch-specific context
            # OPTIMIZATION: Convert batch_id to string once, outside the loop
            batch_id_str = str(batch_id)
            records_with_meta = []
            for r in records:
                # Copy to avoid mutating original
                record = r.copy()
                # Ensure batch ID is set correctly for this write operation
                record["_source_batch_id"] = batch_id_str
                records_with_meta.append(record)

            table_name = (
                self._table_config.silver_table
                or f"{self._provider}.{self._entity_type}"
            )

            # Pass write mode directly without silent degradation (R1 refactoring)
            # SilverWriteMode enum provides type-safe values: MERGE, APPEND, DELETE
            write_mode = self._table_config.silver_write_mode
            # Convert enum to string value for storage port compatibility
            mode_value = (
                write_mode.value if hasattr(write_mode, "value") else write_mode
            )
            silver_mode = cast(Literal["merge", "append", "delete"], mode_value)

            await self._storage.write_silver(
                table_name=table_name,
                records=records_with_meta,
                primary_keys=list(self._table_config.primary_keys),
                schema=self._silver_schema,
                mode=silver_mode,
                on_schema_mismatch=self._table_config.on_schema_mismatch,
            )
            self._end_span(span)
        except Exception as e:
            self._end_span(span, e)
            raise

    async def write_gold(self, records: list[dict[str, Any]]) -> None:
        """Write records to Gold layer with validation.

        Filters columns to match Gold schema, validates records.
        Passes ingestion_ts and run_id from context for audit correlation (ADR-014).

        Args:
            records: Transformed Gold records.

        Raises:
            SchemaViolationError: If validation fails.
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_gold")

        span = self._start_span("write_gold", "gold", len(records))

        try:
            gold_schema = self._config.gold_schema

            # Filter records to only include columns defined in Gold schema
            # This ensures strict schema validation passes (REQ-DATA-009).
            # Uses cached schema columns to avoid per-batch introspection.
            if self._gold_schema_columns:
                records = [
                    {k: r[k] for k in self._gold_schema_columns if k in r}
                    for r in records
                ]

            # Validate Gold records
            result = self._gold_validator.validate(records)
            if not result.valid:
                raise SchemaViolationError("gold", result.errors)

            table_name = (
                self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
            )

            # Pass write mode directly without silent degradation (R1 refactoring)
            # GoldWriteMode enum provides type-safe values: APPEND, SCD2, OVERWRITE
            write_mode = self._table_config.gold_write_mode
            # Convert enum to string value for storage port compatibility
            mode_value = (
                write_mode.value if hasattr(write_mode, "value") else write_mode
            )
            gold_mode = cast(Literal["overwrite", "append", "scd2"], mode_value)

            # Pass ingestion_ts and run_id for audit correlation (ADR-014)
            await self._storage.write_gold(
                table_name=table_name,
                records=records,
                schema=gold_schema,
                primary_keys=list(self._table_config.primary_keys),
                mode=gold_mode,
                ingestion_ts=self._context.started_at,
                run_id=self._context.run_id,
            )
            self._end_span(span)
        except Exception as e:
            self._end_span(span, e)
            raise

    def _get_schema_columns(self, schema: Any) -> set[str] | None:
        """Extract column names from Pandera schema.

        Args:
            schema: Pandera DataFrameModel or DataFrameSchema.

        Returns:
            Set of column names, or None if schema is not recognized.

        """
        # Handle Pandera DataFrameModel (class with to_schema method)
        if hasattr(schema, "to_schema"):
            try:
                converted = schema.to_schema()
                return set(converted.columns.keys())
            except Exception:
                pass

        # Handle Pandera DataFrameSchema (instance with columns dict)
        if hasattr(schema, "columns"):
            return set(schema.columns.keys())

        return None

    def log_and_track_write_error(
        self, layer: str, error: Exception, batch_id: BatchID
    ) -> None:
        """Log write error and track metrics.

        Args:
            layer: Layer name (bronze, silver, gold).
            error: Exception that occurred.
            batch_id: Identifier for the batch.

        """
        error_type = self._error_classifier.classify(error)
        self._context.logger.error(
            "layer_write_failed",
            layer=layer,
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)
