"""Core record processing logic for BioETL pipelines.

Responsible for the Extract -> Bronze -> Silver -> Gold data flow.
Delegates specific layer logic to specialized handlers.

Refactored to match project standards:
- Use PipelineContext.started_at for timestamps (Phase 5).
- Removed explicit datetime.now() calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.handlers.layer_handlers import (
    BronzeLayerHandler,
    GoldLayerHandler,
    SilverLayerHandler,
)
from bioetl.domain.exceptions import (
    DataQualityThresholdError,
    PipelineShutdownError,
    ProcessingError,
)
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort


@dataclass
class BatchResult:
    """Result of processing a batch."""

    bronze_count: int = 0
    silver_count: int = 0
    gold_count: int = 0
    quarantined_count: int = 0
    errors: list[str] = field(default_factory=list)


class RecordProcessor:
    """Orchestrates record processing through Bronze, Silver, and Gold layers.

    Coordinates the flow of data using specialized handlers for each layer.
    Ensures data quality, metrics recording, and error handling.
    """

    def __init__(
        self,
        config: PipelineConfig,
        table_config: TableConfig,
        dq_config: DQConfig,
        services: PipelineServices,
        transformer: BaseTransformer,
        context: PipelineContext,
        silver_schema: Any,
        gold_schema: Any | None = None,
        gold_transformer: Any | None = None,
    ) -> None:
        """Initialize the record processor.

        Args:
            config: Pipeline configuration
            table_config: Table configuration (names, primary keys)
            dq_config: Data quality configuration
            services: Injected infrastructure services
            transformer: Transformer for Bronze -> Silver
            context: Pipeline execution context
            silver_schema: Pandera schema for Silver layer
            gold_schema: Optional Pandera schema for Gold layer
            gold_transformer: Optional transformer for Silver -> Gold

        """
        self._config = config
        self._table_config = table_config
        self._dq_config = dq_config
        self._services = services
        self._transformer = transformer
        self._context = context
        self._logger: LoggerPort = context.logger
        self._metrics_recorder = BatchMetricsRecorder(services.metrics, context)

        # Initialize handlers
        self._bronze_handler = BronzeLayerHandler(
            storage=services.storage.bronze,
            provider=config.provider,
            entity=config.entity_type,
            run_id=context.run_id,
            run_type=context.run_type,
            logger=self._logger,
        )

        self._silver_handler = SilverLayerHandler(
            storage=services.storage.delta,
            quarantine_manager=services.quarantine,
            schema=silver_schema,
            transformer=transformer,
            table_config=table_config,
            dq_config=dq_config,
            logger=self._logger,
            metrics_recorder=self._metrics_recorder,
        )

        self._gold_handler = GoldLayerHandler(
            storage=services.storage.gold,
            schema=gold_schema,
            config=config,  # Pass full config for gold filters
            table_config=table_config,
            logger=self._logger,
            gold_transformer=gold_transformer,
        )

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> BatchResult:
        """Process a batch of records through all layers.

        Args:
            records: Raw records from source
            batch_id: Batch identifier

        Returns:
            BatchResult with processing statistics

        """
        if not records:
            return BatchResult()

        # Use timestamp from context (Single Source of Time)
        ingestion_ts = self._context.started_at

        # Start metrics recording
        self._metrics_recorder.start_batch(batch_id, len(records))

        try:
            # Bronze Layer
            bronze_file = await self._bronze_handler.handle(
                records,
                batch_id,
                ingestion_ts,  # Pass timestamp
            )

            # Silver Layer
            silver_result = await self._silver_handler.handle(
                records,
                self._context,
                batch_id,
                bronze_file,
                ingestion_ts,  # Pass timestamp
            )

            # Check DQ thresholds
            self._check_dq_thresholds(
                total_records=len(records),
                quarantined_count=silver_result.quarantined_count,
            )

            # Gold Layer
            gold_count = 0
            if silver_result.records:
                gold_count = await self._gold_handler.handle(
                    silver_result.records,
                    self._context,
                )

            # Update final metrics
            self._metrics_recorder.record_success(
                bronze_count=len(records),
                silver_count=len(silver_result.records),
                gold_count=gold_count,
                quarantined_count=silver_result.quarantined_count,
            )

            return BatchResult(
                bronze_count=len(records),
                silver_count=len(silver_result.records),
                gold_count=gold_count,
                quarantined_count=silver_result.quarantined_count,
            )

        except PipelineShutdownError:
            self._logger.info("Pipeline shutdown requested during batch processing")
            raise

        except DataQualityThresholdError:
            # DQ errors are critical but handled specifically
            self._metrics_recorder.record_failure("data_quality_error")
            raise

        except Exception as e:
            self._logger.error("Batch processing failed", error=str(e))
            self._metrics_recorder.record_failure("processing_error")
            raise ProcessingError(f"Failed to process batch {batch_id}: {e}") from e

    def _check_dq_thresholds(self, total_records: int, quarantined_count: int) -> None:
        """Check if data quality thresholds are exceeded."""
        if total_records == 0:
            return

        error_rate = quarantined_count / total_records

        # Log warning if soft threshold exceeded
        if error_rate > self._dq_config.soft_fail_threshold:
            self._logger.warning(
                "DQ soft threshold exceeded",
                error_rate=error_rate,
                threshold=self._dq_config.soft_fail_threshold,
                quarantined=quarantined_count,
                total=total_records,
            )

        # Raise error if hard threshold exceeded
        if error_rate > self._dq_config.hard_fail_threshold:
            raise DataQualityThresholdError(
                f"DQ hard threshold exceeded: {error_rate:.2%} > {self._dq_config.hard_fail_threshold:.2%}",
                error_rate=error_rate,
                threshold=self._dq_config.hard_fail_threshold,
            )
