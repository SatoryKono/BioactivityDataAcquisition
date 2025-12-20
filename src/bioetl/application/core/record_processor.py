"""
Processes a batch of records through the Bronze, Silver, and Gold layers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
        dq_config: DQConfig | None = None,
        table_config: TableConfig | None = None,
    ):
        self._storage = services.storage
        self._metrics = services.metrics
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
        self._dq_config = dq_config
        self._table_config = table_config or TableConfig()

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
                batch_id=str(batch_id)
            )
            if self._metrics:
                pipeline_label = f"{self._provider}_{self._entity_type}"
                self._metrics.increment_counter(
                    "errors_total",
                    1,
                    {"pipeline": pipeline_label, "stage": "bronze_write", "error_code": error_type.value},
                )
            # Re-raise to trigger checkpointing logic in Executor or termination
            # Critical persistence failure means we cannot proceed with this batch
            raise

        records_bronze = len(records)
        if self._metrics:
            pipeline_label = f"{self._provider}_{self._entity_type}"
            run_type_label = self._context.run_type.value

            self._metrics.observe_histogram(
                "batch_size_records",
                records_bronze,
                {"pipeline": pipeline_label, "stage": "bronze"},
            )
            self._metrics.increment_counter(
                "records_processed_total",
                records_bronze,
                {"pipeline": pipeline_label, "stage": "bronze", "run_type": run_type_label},
            )

        # 2. Transform and collect Silver/Gold
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for raw_record in records:
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                transformed = await self._transform(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_filter(record_context, transformed):
                        gold_records.append(transformed)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    records_quarantined += 1
                    if self._metrics:
                        # Need to re-compute pipeline label here as it is computed later in original code
                        pipeline_label = f"{self._provider}_{self._entity_type}"
                        self._metrics.increment_counter(
                            "errors_total",
                            1,
                            {"pipeline": pipeline_label, "stage": "transform", "error_code": error_type.value},
                        )
                else:
                    raise

        # Check DQ thresholds
        if self._dq_config and records:
            error_rate = records_quarantined / len(records)
            if self._dq_config.hard_fail_threshold and error_rate >= self._dq_config.hard_fail_threshold:
                raise DataQualityThresholdError(error_rate, self._dq_config.hard_fail_threshold)
            if self._dq_config.soft_fail_threshold and error_rate >= self._dq_config.soft_fail_threshold:
                self._context.logger.warning("DQ Soft Threshold exceeded", error_rate=error_rate)

        if self._metrics:
            pipeline_label = f"{self._provider}_{self._entity_type}"
            run_type_label = self._context.run_type.value

            self._metrics.increment_counter(
                "records_processed_total",
                records_quarantined,
                {"pipeline": pipeline_label, "stage": "quarantined", "run_type": run_type_label},
            )
            self._metrics.increment_counter(
                "records_processed_total",
                len(silver_records),
                {"pipeline": pipeline_label, "stage": "silver", "run_type": run_type_label},
            )
            self._metrics.increment_counter(
                "records_processed_total",
                len(gold_records),
                {"pipeline": pipeline_label, "stage": "gold", "run_type": run_type_label},
            )

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
                if self._metrics:
                    pipeline_label = f"{self._provider}_{self._entity_type}"
                    self._metrics.increment_counter(
                        "errors_total",
                        1,
                        {"pipeline": pipeline_label, "stage": "silver_write", "error_code": error_type.value},
                    )
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
                if self._metrics:
                    pipeline_label = f"{self._provider}_{self._entity_type}"
                    self._metrics.increment_counter(
                        "errors_total",
                        1,
                        {"pipeline": pipeline_label, "stage": "gold_write", "error_code": error_type.value},
                    )
                raise

        return BatchResult(
            bronze_count=records_bronze,
            silver_count=len(silver_records),
            gold_count=len(gold_records),
            quarantined_count=records_quarantined,
        )

    async def _write_bronze_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID, ingestion_ts: datetime
    ) -> None:
        # Sort keys for deterministic output
        record_bytes = [(json.dumps(r, sort_keys=True) + "\n").encode("utf-8") for r in records]
        await self._storage.write_bronze(
            records=iter(record_bytes),
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
        table_name = self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
        await self._storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=self._table_config.primary_keys,
            schema=self._silver_schema,
        )

    async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
        # Use configured table name or default
        table_name = self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
        await self._storage.write_gold(
            table_name=table_name, records=records, mode="append"
        )
