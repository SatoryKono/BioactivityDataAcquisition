"""Batch writing to Bronze, Silver, and Gold layers.

Handles all storage operations with proper metadata enrichment.
Extracted from RecordProcessor for single responsibility (SRP).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import SchemaViolationError

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

        """
        self._storage = storage
        self._context = context
        self._config = config
        self._gold_validator = gold_validator
        self._error_classifier = error_classifier
        self._batch_metrics = batch_metrics
        self._tracer = tracer

        # Convenience properties
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config

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

        """
        span = self._start_span("write_bronze", "bronze", len(records), batch_id)

        try:
            # Serialize with deterministic key ordering
            json_strings = [json.dumps(r, sort_keys=True) for r in records]

            # Sort for deterministic file content
            json_strings.sort()

            # Create generator for bytes
            record_bytes = ((s + "\n").encode("utf-8") for s in json_strings)

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

        """
        span = self._start_span("write_silver", "silver", len(records), batch_id)

        try:
            # Records already have lineage fields from BaseTransformer.entity_to_silver_record
            # But we need to ensure they are present and correct, especially source_batch_id
            # which might be None in entity if not passed during creation.

            # We update _source_batch_id here as it is batch-specific context
            records_with_meta = []
            for r in records:
                # Copy to avoid mutating original
                record = r.copy()
                # Ensure batch ID is set correctly for this write operation
                record["_source_batch_id"] = str(batch_id)
                records_with_meta.append(record)

            table_name = (
                self._table_config.silver_table
                or f"{self._provider}.{self._entity_type}"
            )

            # For "overwrite" mode, use "append" for batch writes
            write_mode = self._table_config.silver_write_mode
            if write_mode == "overwrite":
                write_mode = "append"

            await self._storage.write_silver(
                table_name=table_name,
                records=records_with_meta,
                primary_keys=list(self._table_config.primary_keys),
                schema=self._silver_schema,
                mode=write_mode,
                on_schema_mismatch=self._table_config.on_schema_mismatch,
            )
            self._end_span(span)
        except Exception as e:
            self._end_span(span, e)
            raise

    async def write_gold(self, records: list[dict[str, Any]]) -> None:
        """Write records to Gold layer with validation.

        Filters columns to match Gold schema, validates records.

        Args:
            records: Transformed Gold records.

        Raises:
            SchemaViolationError: If validation fails.

        """
        span = self._start_span("write_gold", "gold", len(records))

        try:
            gold_schema = self._config.gold_schema
            schema_columns = self._get_schema_columns(gold_schema)

            # Filter to only include columns defined in Gold schema
            if schema_columns:
                records = [
                    {k: v for k, v in r.items() if k in schema_columns} for r in records
                ]

            # Validate Gold records
            result = self._gold_validator.validate(records)
            if not result.valid:
                raise SchemaViolationError("gold", result.errors)

            table_name = (
                self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
            )

            # For "overwrite" mode, use "append" for batch writes
            write_mode = self._table_config.gold_write_mode
            if write_mode == "overwrite":
                write_mode = "append"

            await self._storage.write_gold(
                table_name=table_name,
                records=records,
                schema=gold_schema,
                primary_keys=list(self._table_config.primary_keys),
                mode=write_mode,
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
            f"{layer} write failed",
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)
