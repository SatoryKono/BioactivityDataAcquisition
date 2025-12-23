"""
Processes a batch of records through the Bronze, Silver, and Gold layers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.handlers.layer_handlers import (
    BronzeLayerHandler,
    GoldLayerHandler,
    SilverLayerHandler,
)
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.exceptions import DataQualityThresholdError
from bioetl.domain.types import LayerType

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import GoldFilterCallback, TransformCallback
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
    """
    Handles the transformation and writing of a single batch of records.
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
        gold_validator: GoldValidatorPort,
    ):
        self._storage = services.storage
        self._quarantine_manager = QuarantineManager(
            quarantine_port=services.quarantine,
            pipeline_name=config.pipeline_name,
        )
        self._error_classifier = error_classifier
        self._context = context
        self._config = config
        self._dq_config = config.dq_config

        # Convenience properties
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config

        # Instantiate Metrics Recorder
        pipeline_label = f"{self._provider}_{self._entity_type}"
        run_type_label = self._context.run_type.value
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, run_type_label
        )

        # Instantiate Handlers
        self._bronze_handler = BronzeLayerHandler()
        self._silver_handler = SilverLayerHandler(
            transform_callback=transform_callback,
            table_config=config.table_config,
            quarantine_manager=self._quarantine_manager,
            error_classifier=error_classifier,
            metrics=self._batch_metrics,
        )
        self._gold_handler = GoldLayerHandler(
            gold_validator, gold_filter_callback, config.table_config
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

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> BatchResult:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        ingestion_ts = datetime.now(UTC)

        # 1. Write to Bronze
        try:
            records_count, bronze_bytes = self._bronze_handler.prepare_batch(records)
            if bronze_bytes:
                await self._storage.write_bronze(
                    records=bronze_bytes,
                    provider=self._provider,
                    entity=self._entity_type,
                    date=ingestion_ts,
                    batch_id=batch_id,
                    run_id=self._context.run_id,
                    run_type=self._context.run_type,
                )
        except Exception as e:
            self._log_and_track_write_error("bronze", e, batch_id)
            raise

        self._batch_metrics.track_batch_size("bronze", records_count)
        self._batch_metrics.track_processed_records("bronze", records_count)

        # 2. Transform (Silver) - with Quarantine Handling
        # Logic is now delegated to SilverLayerHandler which encapsulates Quarantine.
        # Returns clean records for Gold processing and enriched records for Silver storage.
        clean_records, enriched_records, records_quarantined = await self._silver_handler.prepare_batch(
            self._context, records, batch_id, ingestion_ts
        )

        self._collect_dq_stats(records, records_quarantined)

        # Update metrics
        self._batch_metrics.track_processed_records("quarantined", records_quarantined)
        self._batch_metrics.track_processed_records("silver", len(enriched_records))

        # 3. Write to Silver
        if enriched_records:
            try:
                table_name = (
                    self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
                )
                await self._storage.write_silver(
                    table_name=table_name,
                    records=enriched_records,
                    primary_keys=self._table_config.primary_keys,
                    schema=self._silver_schema,
                    mode=self._silver_handler.get_write_mode(), # Use handler for mode logic
                )
            except Exception as e:
                self._log_and_track_write_error("silver", e, batch_id)
                raise

        # 4. Prepare & Write to Gold
        gold_records = []
        try:
             # Use GoldHandler to filter and validate using CLEAN records
             gold_records = self._gold_handler.prepare_batch(self._context, clean_records, batch_id)
        except Exception as e:
             # Validation error is critical/write error for Gold layer
             self._log_and_track_write_error("gold_validation", e, batch_id)
             raise

        self._batch_metrics.track_processed_records("gold", len(gold_records))

        if gold_records:
            try:
                table_name = (
                    self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
                )
                await self._storage.write_gold(
                    table_name=table_name,
                    records=gold_records,
                    primary_keys=self._table_config.primary_keys,
                    mode=self._gold_handler.get_write_mode(),
                )
            except Exception as e:
                self._log_and_track_write_error("gold", e, batch_id)
                raise

        return BatchResult(
            bronze_count=records_count,
            silver_count=len(enriched_records),
            gold_count=len(gold_records),
            quarantined_count=records_quarantined,
        )

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

