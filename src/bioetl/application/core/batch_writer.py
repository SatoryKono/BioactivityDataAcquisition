"""Batch writing to Bronze, Silver, and Gold layers.

Handles all storage operations with proper metadata enrichment.
Extracted from RecordProcessor for single responsibility (SRP).

Safety Guard (RULES.md §4.6):
    Lock validation is performed at this Application layer BEFORE any write
    operation. This ensures Infrastructure layer (Writers) remain pure I/O
    adapters without knowledge of locking mechanisms.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast

import orjson

from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.domain.composite.config import DataSchemaConfig
from bioetl.domain.exceptions import BioETLError, SchemaViolationError
from bioetl.domain.locking import LockNotHeldError
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from typing import Any as SpanType

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import GoldValidatorPort, StoragePort, TracingPort
    from bioetl.domain.types import BatchID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


_WRITE_SPAN_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)
_SCHEMA_EXTRACTION_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


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
        batch_metrics: BatchMetricsRecorderService,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        data_schema_config: DataSchemaConfig | None = None,
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
            data_schema_config: Optional layer-specific column configuration.

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
        self._gold_schema = config.gold_schema
        self._column_groups = config.column_groups
        self._data_schema = data_schema_config
        self._column_orderer = (
            ColumnOrdererService(
                self._context.logger, column_groups=self._column_groups
            )
            if self._column_groups
            else None
        )

        # Pre-calculate table names and write modes to avoid repeated logic in hot paths
        self._silver_table_name = (
            self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
        )
        self._gold_table_name = (
            self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
        )

        # Pre-calculate write modes
        # Pass write mode directly without silent degradation (R1 refactoring)
        silver_mode_val = self._table_config.silver_write_mode
        self._silver_mode = cast(
            Literal["merge", "append", "delete"],
            silver_mode_val.value
            if hasattr(silver_mode_val, "value")
            else silver_mode_val,
        )

        gold_mode_val = self._table_config.gold_write_mode
        self._gold_mode = cast(
            Literal["overwrite", "append", "scd2"],
            gold_mode_val.value if hasattr(gold_mode_val, "value") else gold_mode_val,
        )

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

        attrs: dict[str, Any] = {  # Any: tracing attribute values are str|int|bool
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
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write records to Bronze layer.

        Serializes records to JSON with deterministic key ordering,
        sorts by content for reproducibility.

        Args:
            records: Raw records to write.
            batch_id: Identifier for the current batch.
            ingestion_ts: Ingestion timestamp from context.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If provided,
                           it will be included in the Bronze metadata sidecar.

        Returns:
            BronzeWriteResult with path, record count, sizes, and checksum
            for downstream lineage tracking (REQ-LINEAGE-001).

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

            bronze_result = await self._storage.write_bronze(
                records=record_bytes,
                provider=self._provider,
                entity=self._entity_type,
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=self._context.run_id,
                run_type=self._context.run_type,
                ingestion_ts=ingestion_ts,
                source_metadata=source_metadata,
            )
            self._end_span(span)
            return bronze_result
        except _WRITE_SPAN_ERRORS as e:
            self._end_span(span, e)
            raise

    async def write_silver(
        self,
        records: list[GoldRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
        """Write records to Silver layer with metadata.

        Enriches records with _run_id, _run_type, _source_batch_id, _ingestion_ts.

        Args:
            records: Transformed Silver records.
            batch_id: Identifier for the source batch.
            ingestion_ts: Ingestion timestamp from context.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

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
            batch_id_str = str(batch_id)

            # OPTIMIZATION: Modify records in-place instead of creating a full copy.
            # This reduces memory allocation overhead by ~35% for large batches.
            # Safety: silver_records are not used after this step in RecordProcessor.
            for r in records:
                r["_source_batch_id"] = batch_id_str

            available_cols = (
                list(self._silver_schema.names)
                if self._silver_schema is not None
                else self._collect_record_columns(records)
            )
            column_order, rename_map = self._resolve_layer_columns(
                "silver", available_cols
            )

            # Apply renames to records if specified
            if rename_map:
                records = self._apply_renames_to_records(records, rename_map)

            silver_result = await self._storage.write_silver(
                table_name=self._silver_table_name,
                records=records,
                primary_keys=list(self._table_config.primary_keys),
                schema=self._silver_schema,
                mode=self._silver_mode,
                partition_cols=list(self._table_config.partition_cols),
                on_schema_mismatch=self._table_config.on_schema_mismatch,
                column_order=column_order,
                bronze_refs=bronze_refs,
                key_nullability_rules=(
                    list(self._config.dq_config.key_nullability_rules)
                    if self._config.dq_config is not None
                    else None
                ),
            )
            self._end_span(span)
            return silver_result
        except _WRITE_SPAN_ERRORS as e:
            self._end_span(span, e)
            raise

    async def write_gold(
        self,
        records: list[GoldRecord],
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write records to Gold layer with validation.

        Filters columns to match Gold schema, validates records.
        Passes ingestion_ts and run_id from context for audit correlation (ADR-014).

        Args:
            records: Transformed Gold records.
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Raises:
            SchemaViolationError: If validation fails.
            LockNotHeldError: If lock is no longer held (Safety Guard §4.6).
        """
        # Safety Guard: validate lock BEFORE write
        await self._validate_lock("write_gold")

        span = self._start_span("write_gold", "gold", len(records))

        try:
            # Filter records to only include columns defined in Gold schema
            # This ensures strict schema validation passes (REQ-DATA-009)
            schema_columns = self._get_schema_columns(self._gold_schema)
            if schema_columns:
                # DQ columns with default values if missing (required by Gold schemas)
                dq_defaults = {"_dq_warn": False, "_dq_error": False}
                records = [
                    {
                        k: r.get(k, dq_defaults.get(k))
                        for k in schema_columns
                        if k in r or k in dq_defaults
                    }
                    for r in records
                ]
            available_cols = (
                list(schema_columns)
                if schema_columns
                else self._collect_record_columns(records)
            )

            # Validate Gold records (before renames)
            result = self._gold_validator.validate(records)
            if not result.valid:
                raise SchemaViolationError("gold", result.errors)

            # Resolve column order and renames for Gold layer
            column_order, rename_map = self._resolve_layer_columns(
                "gold", available_cols
            )

            # Apply renames to records if specified
            if rename_map:
                records = self._apply_renames_to_records(records, rename_map)

            # Pass ingestion_ts, run_id, and silver_refs for audit and lineage (ADR-014, REQ-LINEAGE-002)
            await self._storage.write_gold(
                table_name=self._gold_table_name,
                records=records,
                schema=self._gold_schema,
                primary_keys=list(self._table_config.primary_keys),
                mode=self._gold_mode,
                scd_config=self._config.scd_config,
                column_order=column_order,
                ingestion_ts=self._context.started_at,
                run_id=self._context.run_id,
                silver_refs=silver_refs,
            )
            self._end_span(span)
        except _WRITE_SPAN_ERRORS as e:
            self._end_span(span, e)
            raise

    def _get_schema_columns(
        self, schema: Any
    ) -> set[str] | None:  # Any: Pandera DataFrameModel class varies per entity
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
            except _SCHEMA_EXTRACTION_ERRORS:
                # Catch all: to_schema() may fail for invalid/incomplete schema definitions.
                # Fall through to next schema type check for graceful degradation.
                pass

        # Handle Pandera DataFrameSchema (instance with columns dict)
        if hasattr(schema, "columns"):
            return set(schema.columns.keys())

        return None

    def _collect_record_columns(self, records: list[GoldRecord]) -> list[str]:
        """Collect columns from records in a stable, first-seen order."""
        columns: list[str] = []
        seen: set[str] = set()
        for record in records:
            for key in record:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
        return columns

    def _get_column_order(self, columns: Sequence[str]) -> list[str] | None:
        """Resolve explicit column order from YAML groups if configured."""
        if not self._column_orderer:
            return None
        ordered = self._column_orderer.order_column_names(columns)
        return self._apply_system_prefix_order(ordered)

    def _apply_renames_to_records(
        self, records: list[GoldRecord], rename_map: dict[str, str]
    ) -> list[GoldRecord]:
        """Apply column renames to records.

        Args:
            records: List of record dictionaries.
            rename_map: Mapping of old_name -> new_name.

        Returns:
            List of records with renamed keys.
        """
        if not rename_map:
            return records

        renamed_records = []
        for record in records:
            renamed = {}
            for key, value in record.items():
                new_key = rename_map.get(key, key)
                renamed[new_key] = value
            renamed_records.append(renamed)
        return renamed_records

    def _resolve_layer_columns(
        self, layer: Literal["silver", "gold"], available_columns: Sequence[str]
    ) -> tuple[list[str] | None, dict[str, str]]:
        """Resolve column order and renames for a specific medallion layer.

        Resolution order:
        1. If data_schema has layer-specific config → apply filtering + renames
        2. Otherwise → use shared column_groups via ColumnOrderer

        Args:
            layer: Layer name ("silver" or "gold").
            available_columns: Available columns in the DataFrame/records.

        Returns:
            Tuple of (ordered_columns, rename_map).
            - ordered_columns: Ordered list of columns, or None if no configuration.
            - rename_map: Dict of old_name -> new_name for renaming.
        """
        if not self._data_schema:
            # Fallback to shared column_groups
            return self._get_column_order(available_columns), {}

        layer_config = getattr(self._data_schema, layer, None)
        if not layer_config:
            # No layer-specific config → use shared groups
            return self._get_column_order(available_columns), {}

        # Apply layer-specific filtering
        if not self._column_orderer:
            # No orderer → can't filter by groups, use explicit columns only
            if layer_config.columns:
                return (
                    [c for c in layer_config.columns if c in available_columns],
                    layer_config.rename_fields,
                )
            return None, {}

        # Get filtered and ordered columns (with renames applied to column names)
        ordered_columns = self._column_orderer.filter_by_layer_config(
            available_columns, layer_config
        )
        ordered_columns = self._apply_system_prefix_order(ordered_columns)
        return ordered_columns, layer_config.rename_fields

    def _apply_system_prefix_order(self, columns: list[str]) -> list[str]:
        """Ensure system prefix fields are first and DQ fields are last."""
        from bioetl.domain.schemas.column_order import (
            DQ_FIELDS_SUFFIX,
            LOOKUP_FIELDS_PREFIX,
            SYSTEM_FIELDS_PREFIX,
        )

        if not columns:
            return columns

        column_set = set(columns)
        prefix = [c for c in SYSTEM_FIELDS_PREFIX if c in column_set]
        lookup = [c for c in LOOKUP_FIELDS_PREFIX if c in column_set]
        suffix = [c for c in DQ_FIELDS_SUFFIX if c in column_set]
        middle = [
            c
            for c in columns
            if c not in prefix and c not in lookup and c not in suffix
        ]
        return prefix + lookup + middle + suffix

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
