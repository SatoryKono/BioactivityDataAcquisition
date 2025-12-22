"""
Processes a batch of records through the Bronze, Silver, and Gold layers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.protocols import GoldFilterCallback, TransformCallback
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.config import DQConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityThresholdError
from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


class RecordProcessor:
    """
    Handles the transformation and writing of a single batch of records.
    This class contains the core ETL logic for a batch.
    """

    def __init__(
        self,
        services: PipelineServices,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        silver_schema: Any,
        gold_schema: Any | None = None,
        dq_config: DQConfig | None = None,
        table_config: TableConfig | None = None,
    ):
        self._storage = services.storage
        self._quarantine_manager = QuarantineManager(
            quarantine_port=services.quarantine,
            pipeline_name=pipeline_name,
        )
        self._error_classifier = error_classifier
        self._context = context
        self._provider = provider
        self._entity_type = entity_type
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback
        self._silver_schema = silver_schema
        self._gold_schema = gold_schema
        self._dq_config = dq_config
        self._table_config = table_config or TableConfig()

        # Instantiate Metrics Recorder
        pipeline_label = f"{self._provider}_{self._entity_type}"
        run_type_label = self._context.run_type.value
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, run_type_label
        )

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> BatchResult:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        # Capture consistent timestamp for this batch
        ingestion_ts = datetime.now(UTC)

        # 1. Write to Bronze
        # Pass ingestion_ts to ensure Bronze path matches metadata
        try:
            await self._write_bronze_batch(records, batch_id, ingestion_ts)
        except Exception as e:
            error_type = self._error_classifier.classify(e)
            self._context.logger.error(
                "Bronze write failed",
                error=str(e),
                error_type=error_type.value,
                batch_id=str(batch_id),
            )
            self._batch_metrics.track_error("bronze_write", error_type)
            # Re-raise to trigger checkpointing logic in Executor or termination
            # Critical persistence failure means we cannot proceed with this batch
            raise

        records_bronze = len(records)
        self._batch_metrics.track_batch_size("bronze", records_bronze)
        self._batch_metrics.track_processed_records("bronze", records_bronze)

        # 2. Transform and collect Silver/Gold
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for raw_record in records:
            # Bind logger with record context
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )

            # Use helper method for single record transformation
            try:
                transformed = await self._transform_record(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    # Use helper method for gold filtering
                    if self._gold_filter(record_context, transformed):
                        gold_records.append(transformed)
            except Exception as e:
                # Error handling encapsulated here or in helper?
                # Keeping it here for now to access quarantine manager which uses raw_record
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    records_quarantined += 1
                    self._batch_metrics.track_error("transform", error_type)
                else:
                    raise

        # Check DQ thresholds
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
                error_type = self._error_classifier.classify(e)
                self._context.logger.error(
                    "Silver write failed",
                    error=str(e),
                    error_type=error_type.value,
                    batch_id=str(batch_id),
                )
                self._batch_metrics.track_error("silver_write", error_type)
                raise

        # 4. Write to Gold
        if gold_records:
            try:
                await self._write_gold_batch(gold_records)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                self._context.logger.error(
                    "Gold write failed",
                    error=str(e),
                    error_type=error_type.value,
                    batch_id=str(batch_id),
                )
                self._batch_metrics.track_error("gold_write", error_type)
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
        """Collect DQ stats and check thresholds."""
        if not self._dq_config or not records:
            return

        error_rate = quarantined_count / len(records)
        if (
            self._dq_config.hard_fail_threshold
            and error_rate >= self._dq_config.hard_fail_threshold
        ):
            raise DataQualityThresholdError(
                error_rate, self._dq_config.hard_fail_threshold
            )
        if (
            self._dq_config.soft_fail_threshold
            and error_rate >= self._dq_config.soft_fail_threshold
        ):
            self._context.logger.warning(
                "DQ Soft Threshold exceeded", error_rate=error_rate
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
        # Validate Gold records if schema is present
        if self._gold_schema:
            import pandas as pd

            df = pd.DataFrame(records)
            try:
                # Pandera validation
                self._gold_schema.validate(df, lazy=True)
            except Exception as e:
                # Re-wrap in DQ error or let bubble up depending on strategy
                # For now, we let it bubble up to be caught by the outer loop
                raise e

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
            primary_keys=self._table_config.primary_keys,
            mode=write_mode,
        )
