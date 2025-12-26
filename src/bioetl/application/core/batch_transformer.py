"""Batch transformation from Bronze to Silver/Gold.

Handles record transformation, error handling, and quarantine management.
Extracted from RecordProcessor for single responsibility (SRP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.exceptions import DataQualityThresholdError

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


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""

    silver_records: list[dict[str, Any]]
    gold_records: list[dict[str, Any]]
    quarantined_count: int


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
        quarantine_manager: QuarantineManager,
        batch_metrics: BatchMetricsRecorder,
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
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> TransformResult:
        """Transform all records in batch, returning silver, gold, and quarantine count.

        Args:
            records: Raw Bronze records to transform.
            batch_id: Identifier for the current batch.

        Returns:
            TransformResult with silver records, gold records, and quarantine count.

        Raises:
            DataQualityThresholdError: If DQ hard threshold exceeded.

        """
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

        # Check DQ thresholds after transformation
        self._check_dq_thresholds(records, records_quarantined)

        return TransformResult(
            silver_records=silver_records,
            gold_records=gold_records,
            quarantined_count=records_quarantined,
        )

    def _check_dq_thresholds(
        self, records: list[dict[str, Any]], quarantined_count: int
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

        # Hard fail check
        if dq_config.hard_fail_threshold and error_rate >= dq_config.hard_fail_threshold:
            raise DataQualityThresholdError(error_rate, dq_config.hard_fail_threshold)

        # Soft fail check with detailed logging
        if dq_config.soft_fail_threshold and error_rate >= dq_config.soft_fail_threshold:
            self._context.logger.warning(
                "DQ Soft Threshold exceeded",
                error_rate=round(error_rate, 4),
                threshold=dq_config.soft_fail_threshold,
                quarantined_count=quarantined_count,
                total_count=total_count,
                hard_threshold=dq_config.hard_fail_threshold,
                pipeline=self._config.pipeline_name,
            )
