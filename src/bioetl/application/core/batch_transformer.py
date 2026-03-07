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


from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.exceptions import BioETLError, DataQualityThresholdError
from bioetl.domain.types import BronzeRecord, GoldRecord

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


_TRANSFORM_PROCESSING_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""

    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int = 0


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


class BatchTransformer:
    """Transforms Bronze records to Silver/Gold with error handling.

    Handles:
    - Bronze → Silver transformation via callback
    - Silver → Gold filtering and transformation
    - Error classification and quarantine
    - DQ threshold checking
    """

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
        """Initialize batch transformer.

        Args:
            context: Pipeline execution context.
            config: Record processor configuration.
            error_classifier: Service for error classification.
            quarantine_manager: Manager for quarantining failed records.
            batch_metrics: Metrics recorder for batch processing.
            transform_callback: Callback for Bronze -> Silver transformation.
            gold_filter_callback: Callback for filtering Silver records.
            gold_transform_callback: Callback for Silver -> Gold transformation.

        """
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

        for index, raw_record in enumerate(records, start=start_index):
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                # Pass index to transform callback
                transformed = await self._transform(record_context, raw_record, index)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_filter(record_context, transformed):
                        gold_record = self._gold_transform(record_context, transformed)
                        gold_records.append(gold_record)
            except FilteredOutError as e:
                await self._quarantine_manager.quarantine_filtered_record(
                    raw_record,
                    batch_id,
                    str(e),
                    ingestion_ts=self._context.started_at,
                )
                records_filtered_out += 1
                self._batch_metrics.track_processed_records("filtered_out", 1)
            except _TRANSFORM_PROCESSING_ERRORS as e:
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

        # Check DQ thresholds after transformation
        self._check_dq_thresholds(records, records_quarantined)

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
            filtered_out_count=records_filtered_out,
        )

    def _check_dq_thresholds(
        self, records: list[BronzeRecord], quarantined_count: int
    ) -> None:
        """Check DQ thresholds and raise/warn as appropriate.

        Args:
            records: Original records in the batch.
            quarantined_count: Number of quarantined records.

        Raises:
            DataQualityThresholdError: If hard threshold exceeded.

        """
        if not records:
            return

        total_count = len(records)
        error_rate = quarantined_count / total_count if total_count > 0 else 0.0
        dq_config = self._config.dq_config

        if not dq_config:
            return

        # Hard fail check (hard_fail >= 1.0 treated as disabled, e.g. test mode)
        if (
            dq_config.hard_fail_threshold
            and dq_config.hard_fail_threshold < 1.0
            and error_rate >= dq_config.hard_fail_threshold
        ):
            self._batch_metrics.track_dq_validation_failure(
                stage="transform",
                severity="hard_fail",
            )
            raise DataQualityThresholdError(error_rate, dq_config.hard_fail_threshold)

        # Soft fail check with detailed logging
        if (
            dq_config.soft_fail_threshold
            and error_rate >= dq_config.soft_fail_threshold
        ):
            self._context.logger.warning(
                "DQ Soft Threshold exceeded",
                error_rate=round(error_rate, 4),
                threshold=dq_config.soft_fail_threshold,
                quarantined_count=quarantined_count,
                total_count=total_count,
                hard_threshold=dq_config.hard_fail_threshold,
                pipeline=self._config.pipeline_name,
            )
            self._batch_metrics.track_dq_validation_failure(
                stage="transform",
                severity="soft_fail",
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
        record_context = self._context.bind_logger(
            batch_id=str(batch_id),
            entity_id=raw_record.get("activity_id"),
        )

        try:
            transformed = await self._transform(record_context, raw_record, index)
            if transformed:
                gold_record = None
                if self._gold_filter(record_context, transformed):
                    gold_record = self._gold_transform(record_context, transformed)

                return TransformedRecord(
                    silver_record=transformed,
                    gold_record=gold_record,
                    is_quarantined=False,
                )
            # Transform returned None (filtered out at source)
            return TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=False,
            )
        except FilteredOutError as e:
            await self._quarantine_manager.quarantine_filtered_record(
                raw_record,
                batch_id,
                str(e),
                ingestion_ts=self._context.started_at,
            )
            self._batch_metrics.track_processed_records("filtered_out", 1)
            return TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=False,
                is_filtered_out=True,
            )

        except _TRANSFORM_PROCESSING_ERRORS as e:
            error_type = self._error_classifier.classify(e)
            if error_type.is_data_quality():
                await self._quarantine_manager.quarantine_record(
                    raw_record,
                    error_type,
                    batch_id,
                    str(e),
                    ingestion_ts=self._context.started_at,
                )
                self._batch_metrics.track_error("transform", error_type)
                self._batch_metrics.track_quarantined_records(error_type, 1)

                return TransformedRecord(
                    silver_record=None,
                    gold_record=None,
                    is_quarantined=True,
                )
            raise

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

        for i, raw_record in enumerate(records):
            result = await self.transform_single(raw_record, batch_id, start_index + i)

            if result.is_quarantined:
                records_quarantined += 1
            elif result.is_filtered_out:
                records_filtered_out += 1
            elif result.silver_record is not None:
                silver_records.append(result.silver_record)
                if result.gold_record is not None:
                    gold_records.append(result.gold_record)

        # Check DQ thresholds after transformation
        self._check_dq_thresholds(records, records_quarantined)

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
            filtered_out_count=records_filtered_out,
        )
