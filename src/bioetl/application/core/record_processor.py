"""Processes a batch of records through the Bronze, Silver, and Gold layers."""

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
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


class RecordProcessor:
    """Handles the transformation and writing of a single batch of records.

    This class contains the core ETL logic for a batch.
    """

    def __init__(
        self,
        services: PipelineServices,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        config: RecordProcessorConfig,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
    ):
        """Initialize record processor.

        Args:
            services: Common pipeline services.
            error_classifier: Service for error classification.
            context: Pipeline execution context.
            config: Record processor configuration.
            transform_callback: Callback for Bronze -> Silver transformation.
            gold_filter_callback: Callback for filtering Silver records.
            gold_transform_callback: Callback for Silver -> Gold transformation.
            gold_validator: Validator for Gold layer records.

        """
        self._storage = services.storage
        self._quarantine_manager = QuarantineManager(
            quarantine_port=services.quarantine,
            pipeline_name=config.pipeline_name,
        )
        self._error_classifier = error_classifier
        self._context = context
        self._config = config
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback
        self._gold_transform = gold_transform_callback
        self._gold_validator = gold_validator

        # Convenience properties
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._dq_config = config.dq_config
        self._table_config = config.table_config

        # Instantiate Metrics Recorder
        pipeline_label = f"{self._provider}_{self._entity_type}"
        run_type_label = self._context.run_type.value
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, run_type_label
        )

    def _log_and_track_write_error(
        self, layer: str, error: Exception, batch_id: BatchID
    ) -> None:
        """Log write error and track metrics."""
        error_type = self._error_classifier.classify(error)
        self._context.logger.error(
            f"{layer} write failed",
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)

    async def _transform_records_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Transform all records, returning silver, gold, and quarantine count."""
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for raw_record in records:
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                transformed = await self._transform_record(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_filter(record_context, transformed):
                        gold_record = self._gold_transform(record_context, transformed)
                        gold_records.append(gold_record)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record,
                        error_type,
                        batch_id,
                        str(e),
                        ingestion_ts=self._context.started_at,
                    )
                    records_quarantined += 1
                    self._batch_metrics.track_error("transform", error_type)
                    self._batch_metrics.track_quarantined_records(error_type, 1)
                else:
                    raise

        return silver_records, gold_records, records_quarantined

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> BatchResult:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        # Use context.started_at as single source of time (see ADR-014)
        ingestion_ts = self._context.started_at

        # 1. Write to Bronze
        try:
            await self._write_bronze_batch(records, batch_id, ingestion_ts)
        except Exception as e:
            self._log_and_track_write_error("bronze", e, batch_id)
            raise

        records_bronze = len(records)
        self._batch_metrics.track_batch_size("bronze", records_bronze)
        self._batch_metrics.track_processed_records("bronze", records_bronze)

        # 2. Transform and collect Silver/Gold
        silver_records, gold_records, records_quarantined = (
            await self._transform_records_batch(records, batch_id)
        )
        self._collect_dq_stats(records, records_quarantined)

        # Update metrics
        self._batch_metrics.track_processed_records("quarantined", records_quarantined)
        self._batch_metrics.track_processed_records("silver", len(silver_records))
        self._batch_metrics.track_processed_records("gold", len(gold_records))

        # 3. Write to Silver
        if silver_records:
            try:
                await self._write_silver_batch(silver_records, batch_id, ingestion_ts)
            except Exception as e:
                self._log_and_track_write_error("silver", e, batch_id)
                raise

        # 4. Write to Gold
        if gold_records:
            try:
                await self._write_gold_batch(gold_records)
            except Exception as e:
                self._log_and_track_write_error("gold", e, batch_id)
                raise

        return BatchResult(
            bronze_count=records_bronze,
            silver_count=len(silver_records),
            gold_count=len(gold_records),
            quarantined_count=records_quarantined,
        )

    async def _transform_record(
        self, record_context: PipelineContext, raw_record: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Transform a single record using the callback."""
        return await self._transform(record_context, raw_record)

    def _collect_dq_stats(
        self, records: list[dict[str, Any]], quarantined_count: int
    ) -> None:
        """Collect DQ stats and check thresholds.

        Tracks quarantined records via metrics and checks against
        configured soft/hard thresholds.
        """
        if not records:
            return

        total_count = len(records)
        error_rate = quarantined_count / total_count if total_count > 0 else 0.0

        if not self._dq_config:
            return

        # Hard fail check
        if (
            self._dq_config.hard_fail_threshold
            and error_rate >= self._dq_config.hard_fail_threshold
        ):
            raise DataQualityThresholdError(
                error_rate, self._dq_config.hard_fail_threshold
            )

        # Soft fail check with detailed logging
        if (
            self._dq_config.soft_fail_threshold
            and error_rate >= self._dq_config.soft_fail_threshold
        ):
            self._context.logger.warning(
                "DQ Soft Threshold exceeded",
                error_rate=round(error_rate, 4),
                threshold=self._dq_config.soft_fail_threshold,
                quarantined_count=quarantined_count,
                total_count=total_count,
                hard_threshold=self._dq_config.hard_fail_threshold,
                pipeline=self._config.pipeline_name,
            )

    async def _write_bronze_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        # 1. Serialize all records to JSON strings with deterministic key ordering
        # This avoids serializing twice (once for sort, once for write)
        json_strings = [json.dumps(r, sort_keys=True) for r in records]

        # 2. Sort the JSON strings to ensure deterministic file content
        json_strings.sort()

        # 3. Create generator for bytes
        record_bytes = ((s + "\n").encode("utf-8") for s in json_strings)

        await self._storage.write_bronze(
            records=record_bytes,
            provider=self._provider,
            entity=self._entity_type,
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=self._context.run_id,
            run_type=self._context.run_type,
            ingestion_ts=ingestion_ts,  # Pass from context (single source of time)
        )

    async def _write_silver_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        records_with_meta = [
            {
                **r,
                "_run_id": str(self._context.run_id),
                "_run_type": self._context.run_type.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": ingestion_ts.isoformat(),
            }
            for r in records
        ]
        # Use configured table name or default
        table_name = (
            self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
        )
        # For "overwrite" mode, use "append" for batch writes since table is cleared at run start
        # This allows accumulating batches within a run while still replacing previous run data
        write_mode = self._table_config.silver_write_mode
        if write_mode == "overwrite":
            write_mode = "append"
        await self._storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=self._table_config.primary_keys,
            schema=self._silver_schema,
            mode=write_mode,
        )

    async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
        # Get schema column names for filtering (strict mode requires exact columns)
        gold_schema = self._config.gold_schema
        schema_columns = self._get_schema_columns(gold_schema)

        # Filter records to only include columns defined in Gold schema
        if schema_columns:
            records = [
                {k: v for k, v in r.items() if k in schema_columns} for r in records
            ]

        # Validate Gold records using dedicated validator (SRP)
        result = self._gold_validator.validate(records)
        if not result.valid:
            raise SchemaViolationError("gold", result.errors)

        # Use configured table name or default
        table_name = (
            self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
        )
        # For "overwrite" mode, use "append" for batch writes since table is cleared at run start
        # This allows accumulating batches within a run while still replacing previous run data
        write_mode = self._table_config.gold_write_mode
        if write_mode == "overwrite":
            write_mode = "append"
        await self._storage.write_gold(
            table_name=table_name,
            records=records,
            schema=gold_schema,
            primary_keys=self._table_config.primary_keys,
            mode=write_mode,
        )

    def _get_schema_columns(self, schema: Any) -> set[str] | None:
        """Extract column names from Pandera schema.

        Args:
            schema: Pandera DataFrameModel or DataFrameSchema.

        Returns:
            Set of column names, or None if schema is not recognized.

        """
        # Handle Pandera DataFrameModel (class with to_schema method)
        # Use to_schema() to get actual column names including aliases
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
