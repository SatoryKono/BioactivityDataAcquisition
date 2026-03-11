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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_helpers import (
    accumulate_transform_outcome,
    check_dq_thresholds,
    flush_dq_records,
    flush_filtered_records,
    transform_record_attempt,
    yield_control_if_needed,
)
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.core.quarantine_manager import (
        DQQuarantineEntry,
        FilteredQuarantineEntry,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""

    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int = 0
    records_quarantine_failed: int = 0


@dataclass(frozen=True, slots=True)
class TransformedRecord:
    """Single transformed record with routing info.

    Used in streaming mode to yield individual records.

    Attributes:
        silver_record: The transformed Silver record (None if quarantined).
        gold_record: The Gold record (None if filtered out or quarantined).
        is_quarantined: Whether this record was quarantined due to DQ error.

    """

    silver_record: BronzeRecord | None
    gold_record: GoldRecord | None
    is_quarantined: bool
    is_filtered_out: bool = False
    quarantine_write_failed: bool = False


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
        silver_records: list[BronzeRecord] = []
        gold_records: list[GoldRecord] = []
        records_quarantined = 0
        records_filtered_out = 0
        filtered_records: list[FilteredQuarantineEntry] = []
        dq_records: list[DQQuarantineEntry] = []
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

            quarantined_delta, filtered_delta = accumulate_transform_outcome(
                attempt=attempt,
                silver_records=silver_records,
                gold_records=gold_records,
                filtered_records=filtered_records,
                dq_records=dq_records,
            )
            records_quarantined += quarantined_delta
            records_filtered_out += filtered_delta

        filtered_failed = await flush_filtered_records(
            context=self._context,
            quarantine_manager=self._quarantine_manager,
            records=filtered_records,
            batch_id=batch_id,
        )
        dq_failed = await flush_dq_records(
            context=self._context,
            quarantine_manager=self._quarantine_manager,
            records=dq_records,
            batch_id=batch_id,
        )

        check_dq_thresholds(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            records=records,
            quarantined_count=records_quarantined,
        )

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
            filtered_out_count=records_filtered_out,
            records_quarantine_failed=filtered_failed + dq_failed,
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

        if attempt.silver_record is not None:
            return TransformedRecord(
                silver_record=attempt.silver_record,
                gold_record=attempt.gold_record,
                is_quarantined=False,
            )
        if attempt.filtered_entry is not None:
            failed = await flush_filtered_records(
                context=self._context,
                quarantine_manager=self._quarantine_manager,
                records=[attempt.filtered_entry],
                batch_id=batch_id,
            )
            return TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=False,
                is_filtered_out=True,
                quarantine_write_failed=failed > 0,
            )
        if attempt.dq_entry is not None:
            failed = await flush_dq_records(
                context=self._context,
                quarantine_manager=self._quarantine_manager,
                records=[attempt.dq_entry],
                batch_id=batch_id,
            )
            return TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=True,
                quarantine_write_failed=failed > 0,
            )
        # Transform returned None without explicit quarantine/filtered state.
        return TransformedRecord(
            silver_record=None,
            gold_record=None,
            is_quarantined=False,
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
        silver_records: list[BronzeRecord] = []
        gold_records: list[GoldRecord] = []
        records_quarantined = 0
        records_filtered_out = 0
        records_quarantine_failed = 0
        last_yield_at = time.monotonic()

        for i, raw_record in enumerate(records):
            last_yield_at = await yield_control_if_needed(last_yield_at)
            result = await self.transform_single(raw_record, batch_id, start_index + i)

            if result.quarantine_write_failed:
                records_quarantine_failed += 1
            if result.is_quarantined:
                records_quarantined += 1
            elif result.is_filtered_out:
                records_filtered_out += 1
            elif result.silver_record is not None:
                silver_records.append(result.silver_record)
                if result.gold_record is not None:
                    gold_records.append(result.gold_record)

        check_dq_thresholds(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            records=records,
            quarantined_count=records_quarantined,
        )

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
            filtered_out_count=records_filtered_out,
            records_quarantine_failed=records_quarantine_failed,
        )
