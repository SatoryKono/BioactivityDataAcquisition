"""Batch transformation from Bronze to Silver/Gold.

Handles record transformation, error handling, and quarantine management.
Extracted from RecordProcessor for single responsibility (SRP).

Supports two processing modes:
1. Standard batch processing (transform_batch) - processes all records in memory
2. Streaming processing (transform_stream) - generator-based for memory efficiency
"""

from __future__ import annotations

__all__ = [
    "BatchTransformer",
    "StreamingBatchProcessor",
    "TransformResult",
    "TransformedRecord",
]

import time
from typing import TYPE_CHECKING

from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_helpers import (
    TransformedRecord,
    TransformResult,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    create_transform_aggregation_state,
    finalize_batch_transform_result,
    finalize_stream_transform_result,
    route_single_transform_attempt,
    transform_record_attempt,
    yield_control_if_needed,
)
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID


class BatchTransformer:
    """Transforms Bronze records to Silver/Gold with error handling and DQ checks."""

    def __init__(
        self,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        quarantine_manager: QuarantineManagerService,
        batch_metrics: BatchMetricsRecorderService,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
    ) -> None:
        """Initialize batch transformer."""
        self._context = context
        self._config = config
        self._error_classifier = error_classifier
        self._quarantine_manager = quarantine_manager
        self._batch_metrics = batch_metrics
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback
        self._gold_transform = gold_transform_callback

    async def transform_batch(
        self, records: list[BronzeRecord], batch_id: BatchID, start_index: int = 0
    ) -> TransformResult:
        """Transform all records in batch, returning silver, gold, and quarantine count.

        Args:
            records: Raw Bronze records to transform.
            batch_id: Identifier for the current batch.
            start_index: The starting index for records in this batch.

        Returns:
            TransformResult with silver records, gold records, and quarantine count.

        Raises:
            DataQualityThresholdError: If DQ hard threshold exceeded.

        """
        state = create_transform_aggregation_state()
        last_yield_at = time.monotonic()

        for index, raw_record in enumerate(records, start=start_index):
            last_yield_at = await yield_control_if_needed(last_yield_at)
            attempt = await transform_record_attempt(
                context=self._context,
                error_classifier=self._error_classifier,
                batch_metrics=self._batch_metrics,
                transform=self._transform,
                gold_filter=self._gold_filter,
                gold_transform=self._gold_transform,
                raw_record=raw_record,
                batch_id=batch_id,
                index=index,
            )

            apply_transform_outcome_to_state(
                state=state,
                attempt=attempt,
            )

        return await finalize_batch_transform_result(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            quarantine_manager=self._quarantine_manager,
            state=state,
            batch_id=batch_id,
            records=records,
        )

    async def transform_single(
        self, raw_record: BronzeRecord, batch_id: BatchID, index: int = 0
    ) -> TransformedRecord:
        """Transform a single record (for streaming mode).

        This method processes one record at a time, enabling memory-efficient
        streaming processing of large datasets.

        Args:
            raw_record: Single Bronze record to transform.
            batch_id: Identifier for the current batch.
            index: Sequential index of the record in the pipeline run.

        Returns:
            TransformedRecord with silver/gold records or quarantine status.

        """
        attempt = await transform_record_attempt(
            context=self._context,
            error_classifier=self._error_classifier,
            batch_metrics=self._batch_metrics,
            transform=self._transform,
            gold_filter=self._gold_filter,
            gold_transform=self._gold_transform,
            raw_record=raw_record,
            batch_id=batch_id,
            index=index,
        )
        return await route_single_transform_attempt(
            context=self._context,
            quarantine_manager=self._quarantine_manager,
            attempt=attempt,
            batch_id=batch_id,
        )

    async def transform_stream(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int = 0,
    ) -> TransformResult:
        """Transform records using streaming mode with memory efficiency.

        This method processes records one-at-a-time but accumulates results
        for batch writing. Use this for moderate memory savings while
        maintaining batch write semantics.

        For full streaming (no accumulation), use iter_transform_stream.

        Args:
            records: Raw Bronze records to transform.
            batch_id: Identifier for the current batch.
            start_index: Starting index for the batch.

        Returns:
            TransformResult with silver records, gold records, and quarantine count.

        Raises:
            DataQualityThresholdError: If DQ hard threshold exceeded.

        """
        state = create_transform_aggregation_state()
        last_yield_at = time.monotonic()

        for i, raw_record in enumerate(records):
            last_yield_at = await yield_control_if_needed(last_yield_at)
            result = await self.transform_single(raw_record, batch_id, start_index + i)
            apply_stream_transform_result_to_state(
                state=state,
                result=result,
            )

        return finalize_stream_transform_result(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            state=state,
            records=records,
        )
