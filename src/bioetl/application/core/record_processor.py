"""Processes a batch of records through the Bronze, Silver, and Gold layers.

Observability (O2):
- Nested spans for each stage: transform → write_bronze → write_silver → write_gold
- Span attributes include record counts and batch metadata
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.handlers.layer_handlers import (
    BronzeLayerHandler,
    GoldLayerHandler,
    HandlerContext,
    SilverLayerHandler,
)
from bioetl.application.core.quarantine_manager import QuarantineManager

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import TransformCallback
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports.gold_transformer import GoldTransformerPort
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
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
    Refactored to delegate logic to specific layer handlers (R1).

    Observability (O2):
    - Nested spans for transform, write_bronze, write_silver, write_gold
    - Each span includes relevant record counts and status
    """

    def __init__(
        self,
        services: PipelineServices,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        config: RecordProcessorConfig,
        transform_callback: TransformCallback,
        gold_transformer: GoldTransformerPort,
        gold_validator: GoldValidatorPort,
        tracer: TracingPort | None = None,
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
            tracer: Optional tracing port for distributed tracing.

        """
        self._context = context

        # Initialize Metrics Recorder
        pipeline_label = f"{config.provider}_{config.entity_type}"
        run_type_label = context.run_type.value
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, run_type_label
        )

        # Initialize Quarantine Manager
        quarantine_manager = QuarantineManager(
            quarantine_port=services.quarantine,
            pipeline_name=config.pipeline_name,
        )

        # Create Shared Context
        handler_context = HandlerContext(
            pipeline_context=context,
            storage=services.storage,
            metrics=self._batch_metrics,
            error_classifier=error_classifier,
            tracer=tracer,
            config=config,
        )

        # Initialize Layer Handlers
        self._bronze_handler = BronzeLayerHandler(handler_context)

        self._silver_handler = SilverLayerHandler(
            context=handler_context,
            quarantine_manager=quarantine_manager,
            transform_callback=transform_callback,
            gold_transformer=gold_transformer,
        )

        self._gold_handler = GoldLayerHandler(
            context=handler_context,
            validator=gold_validator,
        )

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> BatchResult:
        """Process a batch of records through Bronze -> Silver -> Gold.

        Delegates to layer handlers.
        """
        # Use context.started_at as single source of time (see ADR-014)
        ingestion_ts = self._context.started_at

        # 1. Write to Bronze
        bronze_count = await self._bronze_handler.write_bronze(
            records, batch_id, ingestion_ts
        )

        # 2. Transform and Write Silver
        # Also returns gold records ready for processing and quarantined count
        silver_count, gold_records, quarantined_count = (
            await self._silver_handler.transform_and_write(
                records, batch_id, ingestion_ts
            )
        )

        # 3. Validate and Write Gold
        gold_count = await self._gold_handler.write_gold(
            gold_records, batch_id
        )

        return BatchResult(
            bronze_count=bronze_count,
            silver_count=silver_count,
            gold_count=gold_count,
            quarantined_count=quarantined_count,
        )
