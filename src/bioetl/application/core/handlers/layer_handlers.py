"""Layer Handlers for RecordProcessor.

Implements the R1 refactoring (RecordProcessor Decomposition).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.exceptions import DataQualityThresholdError, SchemaViolationError

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.protocols import TransformCallback
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports.gold_transformer import GoldTransformerPort
    from bioetl.domain.ports import (
        GoldValidatorPort,
        StoragePort,
        TracingPort,
    )
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class HandlerContext:
    """Shared context for layer handlers."""

    pipeline_context: PipelineContext
    storage: StoragePort
    metrics: BatchMetricsRecorder
    error_classifier: ErrorClassifier
    tracer: TracingPort | None
    config: RecordProcessorConfig

    def start_span(self, name: str, **attributes: Any) -> Any:
        """Start a tracing span if tracer is available."""
        if not self.tracer:
            return None
        otel_tracer = self.tracer.get_tracer("bioetl.processor")
        span = otel_tracer.start_as_current_span(name, attributes=attributes)
        span.__enter__()
        return span

    def end_span(self, span: Any, error: Exception | None = None) -> None:
        """End a tracing span."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    def log_and_track_write_error(
        self, layer: str, error: Exception, batch_id: BatchID
    ) -> None:
        """Log write error and track metrics."""
        error_type = self.error_classifier.classify(error)
        self.pipeline_context.logger.error(
            f"{layer} write failed",
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self.metrics.track_error(f"{layer}_write", error_type)


class BronzeLayerHandler:
    """Handles Bronze layer operations (Raw -> S3/JSONL)."""

    def __init__(self, context: HandlerContext):
        self._ctx = context

    async def write_bronze(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> int:
        """Write raw records to Bronze layer."""
        if not records:
            return 0

        span = self._ctx.start_span(
            "write_bronze",
            **{
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": len(records),
            },
        )

        try:
            # 1. Serialize all records to JSON strings with deterministic key ordering
            json_strings = [json.dumps(r, sort_keys=True) for r in records]

            # 2. Sort the JSON strings to ensure deterministic file content
            json_strings.sort()

            # 3. Create generator for bytes
            record_bytes = ((s + "\n").encode("utf-8") for s in json_strings)

            await self._ctx.storage.write_bronze(
                records=record_bytes,
                provider=self._ctx.config.provider,
                entity=self._ctx.config.entity_type,
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=self._ctx.pipeline_context.run_id,
                run_type=self._ctx.pipeline_context.run_type,
                ingestion_ts=ingestion_ts,
            )
            self._ctx.end_span(span)
        except Exception as e:
            self._ctx.end_span(span, e)
            self._ctx.log_and_track_write_error("bronze", e, batch_id)
            raise

        count = len(records)
        self._ctx.metrics.track_batch_size("bronze", count)
        self._ctx.metrics.track_processed_records("bronze", count)
        return count


class SilverLayerHandler:
    """Handles Silver layer operations (Transformation + Delta Lake)."""

    def __init__(
        self,
        context: HandlerContext,
        quarantine_manager: QuarantineManager,
        transform_callback: TransformCallback,
        gold_transformer: GoldTransformerPort,
    ):
        self._ctx = context
        self._quarantine = quarantine_manager
        self._transform = transform_callback
        self._gold_transformer = gold_transformer

    async def transform_and_write(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> tuple[int, list[dict[str, Any]], int]:
        """Transform Bronze records and write to Silver.

        Returns:
            Tuple of (silver_count, gold_records, quarantined_count).
        """
        if not records:
            return 0, [], 0

        # 1. Transform
        span = self._ctx.start_span(
            "transform",
            **{
                "bioetl.batch_id": str(batch_id),
                "bioetl.input_count": len(records),
            },
        )
        try:
            silver_records, gold_records, records_quarantined = (
                await self._transform_records_batch(records, batch_id)
            )
            if span:
                span.set_attribute("bioetl.silver_count", len(silver_records))
                span.set_attribute("bioetl.gold_count", len(gold_records))
                span.set_attribute("bioetl.quarantined_count", records_quarantined)
            self._ctx.end_span(span)
        except Exception as e:
            self._ctx.end_span(span, e)
            raise

        self._collect_dq_stats(records, records_quarantined)

        # Update metrics
        self._ctx.metrics.track_processed_records("quarantined", records_quarantined)
        self._ctx.metrics.track_processed_records("silver", len(silver_records))

        # 2. Write Silver
        if silver_records:
            span = self._ctx.start_span(
                "write_silver",
                **{
                    "bioetl.batch_id": str(batch_id),
                    "bioetl.record_count": len(silver_records),
                },
            )
            try:
                await self._write_silver_batch(silver_records, batch_id, ingestion_ts)
                self._ctx.end_span(span)
            except Exception as e:
                self._ctx.end_span(span, e)
                self._ctx.log_and_track_write_error("silver", e, batch_id)
                raise

        return len(silver_records), gold_records, records_quarantined

    async def _transform_records_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Transform all records, returning silver, gold, and quarantine count."""
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for raw_record in records:
            record_context = self._ctx.pipeline_context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                transformed = await self._transform(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_transformer.should_process(record_context, transformed):
                        gold_record = self._gold_transformer.transform(record_context, transformed)
                        gold_records.append(gold_record)
            except Exception as e:
                error_type = self._ctx.error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine.quarantine_record(
                        raw_record,
                        error_type,
                        batch_id,
                        str(e),
                        ingestion_ts=self._ctx.pipeline_context.started_at,
                    )
                    records_quarantined += 1
                    self._ctx.metrics.track_error("transform", error_type)
                    self._ctx.metrics.track_quarantined_records(error_type, 1)
                else:
                    raise

        return silver_records, gold_records, records_quarantined

    async def _write_silver_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        records_with_meta = [
            {
                **r,
                "_run_id": str(self._ctx.pipeline_context.run_id),
                "_run_type": self._ctx.pipeline_context.run_type.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": ingestion_ts.isoformat(),
            }
            for r in records
        ]
        table_config = self._ctx.config.table_config
        # Use configured table name or default
        table_name = (
            table_config.silver_table
            or f"{self._ctx.config.provider}.{self._ctx.config.entity_type}"
        )
        # For "overwrite" mode, use "append" for batch writes since table is cleared at run start
        write_mode = table_config.silver_write_mode
        if write_mode == "overwrite":
            write_mode = "append"

        await self._ctx.storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=table_config.primary_keys,
            schema=self._ctx.config.silver_schema,
            mode=write_mode,
        )

    def _collect_dq_stats(
        self, records: list[dict[str, Any]], quarantined_count: int
    ) -> None:
        """Collect DQ stats and check thresholds."""
        if not records:
            return

        total_count = len(records)
        error_rate = quarantined_count / total_count if total_count > 0 else 0.0

        dq_config = self._ctx.config.dq_config
        if not dq_config:
            return

        # Hard fail check
        if (
            dq_config.hard_fail_threshold
            and error_rate >= dq_config.hard_fail_threshold
        ):
            raise DataQualityThresholdError(
                error_rate, dq_config.hard_fail_threshold
            )

        # Soft fail check with detailed logging
        if (
            dq_config.soft_fail_threshold
            and error_rate >= dq_config.soft_fail_threshold
        ):
            self._ctx.pipeline_context.logger.warning(
                "DQ Soft Threshold exceeded",
                error_rate=round(error_rate, 4),
                threshold=dq_config.soft_fail_threshold,
                quarantined_count=quarantined_count,
                total_count=total_count,
                hard_threshold=dq_config.hard_fail_threshold,
                pipeline=self._ctx.config.pipeline_name,
            )


class GoldLayerHandler:
    """Handles Gold layer operations (Validation + Delta Lake)."""

    def __init__(self, context: HandlerContext, validator: GoldValidatorPort):
        self._ctx = context
        self._validator = validator

    async def write_gold(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> int:
        """Validate and write Gold records."""
        if not records:
            return 0

        span = self._ctx.start_span(
            "write_gold",
            **{
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": len(records),
            },
        )

        try:
            # 1. Validate
            await self._validate_records(records)

            # 2. Write
            await self._write_gold_batch(records, self._ctx.pipeline_context.started_at)
            self._ctx.end_span(span)
        except Exception as e:
            self._ctx.end_span(span, e)
            self._ctx.log_and_track_write_error("gold", e, batch_id)
            raise

        count = len(records)
        self._ctx.metrics.track_processed_records("gold", count)
        return count

    async def _validate_records(self, records: list[dict[str, Any]]) -> None:
        # Get schema column names for filtering (strict mode requires exact columns)
        gold_schema = self._ctx.config.gold_schema
        schema_columns = self._get_schema_columns(gold_schema)

        # Filter records to only include columns defined in Gold schema
        if schema_columns:
            # Modify list in-place or return new list?
            # Handler receives pre-transformed records, but we might need to filter columns
            # The original code filtered the list.
            # We can't modify the input list if it's used elsewhere, but here it's passed uniquely.
            # However, to be safe, we'll iterate.
            # Actually, `records` here is the `gold_records` list from Silver handler.
            # We can modify it or create a new one. Creating new one is safer.
            # Wait, Python list is mutable. But here we are assigning `records = ...` which is local.
            # So we are filtering.
            records[:] = [
                {k: v for k, v in r.items() if k in schema_columns} for r in records
            ]

        # Validate Gold records
        result = self._validator.validate(records)
        if not result.valid:
            raise SchemaViolationError("gold", result.errors)

    async def _write_gold_batch(
        self, records: list[dict[str, Any]], ingestion_ts: datetime
    ) -> None:
        table_config = self._ctx.config.table_config
        # Use configured table name or default
        table_name = (
            table_config.gold_table
            or f"{self._ctx.config.provider}.{self._ctx.config.entity_type}"
        )
        # For "overwrite" mode, use "append" for batch writes since table is cleared at run start
        write_mode = table_config.gold_write_mode
        if write_mode == "overwrite":
            write_mode = "append"

        await self._ctx.storage.write_gold(
            table_name=table_name,
            records=records,
            schema=self._ctx.config.gold_schema,
            ingestion_ts=ingestion_ts,
            primary_keys=table_config.primary_keys,
            mode=write_mode,
        )

    def _get_schema_columns(self, schema: Any) -> set[str] | None:
        """Extract column names from Pandera schema."""
        if hasattr(schema, "to_schema"):
            try:
                converted = schema.to_schema()
                return set(converted.columns.keys())
            except Exception:
                pass
        if hasattr(schema, "columns"):
            return set(schema.columns.keys())
        return None
