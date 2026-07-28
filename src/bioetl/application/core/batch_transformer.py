"""Batch transformation from Bronze to Silver/Gold."""

from __future__ import annotations

__all__ = ["BatchTransformer", "StreamingBatchProcessor", "TransformResult", "TransformedRecord"]

import asyncio
from typing import TYPE_CHECKING, cast

from bioetl.application.core._batch_transformer_support import (
    build_default_normalization_processor,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.core.transformer_runtime.attempts import (
    transform_record_attempt,
)
from bioetl.application.core.transformer_runtime.finalization import (
    finalize_batch_transform_result,
    finalize_stream_transform_result,
)
from bioetl.application.core.transformer_runtime.orchestration import (
    collect_batch_transform_state,
    collect_stream_transform_state,
    yield_control_if_needed,
)
from bioetl.application.core.transformer_runtime.quarantine import (
    flush_dq_records,
    flush_filtered_records,
    route_single_transform_attempt,
)
from bioetl.application.core.transformer_runtime.state import (
    TransformedRecord,
    TransformResult,
)
from bioetl.application.core.transformer_runtime.streaming import (
    StreamingBatchProcessor,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.application.core.transformer_runtime.state import RecordTransformOutcome
    from bioetl.application.services.debug_export_service import DebugExportService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID


class BatchTransformer:
    """Transforms Bronze records to Silver/Gold with error handling and DQ checks."""

    def __init__(
        self,
        context: PipelineContext,
        config: RecordProcessorConfig,
        runtime: dict[str, object] | None = None,
        callbacks: dict[str, object] | None = None,
        normalization_processor: RecordNormalizationProcessor | None = None,
        debug_export_service: DebugExportService | None = None,
        **legacy: object,
    ) -> None:
        """Initialize batch transformer.

        Prefer ``runtime`` + ``callbacks`` dicts. Transitional/unit callers may
        pass individual collaborators via keyword args.
        """
        resolved_runtime, resolved_callbacks = _resolve_transformer_bags(
            runtime, callbacks, legacy
        )
        self._context = context
        self._config = config
        self._error_classifier = cast(
            "ErrorClassifier", resolved_runtime["error_classifier"]
        )
        self._quarantine_manager = cast(
            "QuarantineRuntimeService", resolved_runtime["quarantine_manager"]
        )
        self._batch_metrics = cast(
            "BatchMetricsRecorderService", resolved_runtime["batch_metrics"]
        )
        self._transform = cast(
            "TransformCallback", resolved_callbacks["transform_callback"]
        )
        self._gold_filter = cast(
            "GoldFilterCallback", resolved_callbacks["gold_filter_callback"]
        )
        self._gold_transform = cast(
            "GoldTransformCallback", resolved_callbacks["gold_transform_callback"]
        )
        self._debug_export_service = debug_export_service
        self._normalization_processor = (
            normalization_processor
            if normalization_processor is not None
            else build_default_normalization_processor(config)
        )

    async def _transform_attempt(
        self,
        raw_record: BronzeRecord,
        batch_id: BatchID,
        index: int,
    ) -> RecordTransformOutcome:
        """Run the shared per-record transformation flow."""
        return await transform_record_attempt(
            context=self._context,
            error_classifier=self._error_classifier,
            batch_metrics=self._batch_metrics,
            transform=self._transform,
            gold_filter=self._gold_filter,
            gold_transform=self._gold_transform,
            dq_config=self._config.dq_config,
            normalization_processor=self._normalization_processor,
            debug_export_service=self._debug_export_service,
            raw_record=raw_record,
            batch_id=batch_id,
            index=index,
        )

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
        state = await collect_batch_transform_state(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
            transform_attempt=self._transform_attempt,
            yield_control=yield_control_if_needed,
        )

        return await finalize_batch_transform_result(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            state=state,
            records=records,
            flush_filtered_records=lambda: flush_filtered_records(
                context=self._context,
                quarantine_manager=self._quarantine_manager,
                records=state.filtered_records,
                batch_id=batch_id,
            ),
            flush_dq_records=lambda: flush_dq_records(
                context=self._context,
                quarantine_manager=self._quarantine_manager,
                records=state.dq_records,
                batch_id=batch_id,
            ),
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
        attempt = await self._transform_attempt(
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
        state = await collect_stream_transform_state(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
            transform_single=self.transform_single,
            yield_control=yield_control_if_needed,
        )

        return await finalize_stream_transform_result(
            context=self._context,
            config=self._config,
            batch_metrics=self._batch_metrics,
            state=state,
            records=records,
            # Streaming mode routes quarantine side effects per record already.
            flush_filtered_records=lambda: asyncio.sleep(0),
            flush_dq_records=lambda: asyncio.sleep(0),
        )


def _merge_named_keys(
    base: dict[str, object] | None,
    legacy: dict[str, object],
    keys: tuple[str, ...],
) -> dict[str, object]:
    """Copy base and overlay non-None legacy values for the given keys."""
    resolved = dict(base or {})
    for key in keys:
        value = legacy.pop(key, None)
        if value is not None:
            resolved[key] = value
    return resolved


def _resolve_transformer_bags(
    runtime: dict[str, object] | None,
    callbacks: dict[str, object] | None,
    legacy: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Merge runtime/callback dicts with transitional kwargs; reject unknowns."""
    resolved_runtime = _merge_named_keys(
        runtime,
        legacy,
        ("error_classifier", "quarantine_manager", "batch_metrics"),
    )
    resolved_callbacks = _merge_named_keys(
        callbacks,
        legacy,
        ("transform_callback", "gold_filter_callback", "gold_transform_callback"),
    )
    if legacy:
        raise TypeError(
            "BatchTransformer() got unexpected keyword argument(s): "
            + ", ".join(sorted(str(k) for k in legacy))
        )
    return resolved_runtime, resolved_callbacks
