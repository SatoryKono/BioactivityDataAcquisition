"""Per-record transform helpers for batch transformation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
from bioetl.application.core.batch_transformer_attempt_failures import (
    _build_filtered_out_handling_context_from_mapping,
    handle_filtered_out_error,
    handle_transform_processing_error,
)
from bioetl.application.core.batch_transformer_attempt_success import (
    _resolve_gold_filter_details as _resolve_gold_filter_details,
)
from bioetl.application.core.batch_transformer_attempt_success import (
    build_transform_success_outcome,
)
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )
    from bioetl.application.services.debug_export_service import DebugExportService
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID

TRANSFORM_PROCESSING_ERRORS = OPERATION_ERRORS


def bind_record_context(
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
) -> PipelineContext:
    """Create a per-record logger context for transformation."""
    return context.with_source_batch_id(batch_id).bind_logger(
        batch_id=str(batch_id),
        entity_id=raw_record.get("activity_id"),
    )


async def transform_record_attempt(
    *,
    context: PipelineContext,
    error_classifier: ErrorClassifier,
    batch_metrics: BatchMetricsRecorderService,
    transform: TransformCallback,
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
    dq_config: DQConfig | None,
    normalization_processor: RecordNormalizationProcessor | None,
    debug_export_service: DebugExportService | None,
    raw_record: BronzeRecord,
    batch_id: BatchID,
    index: int,
) -> RecordTransformOutcome:
    """Transform one record and classify it before quarantine persistence."""
    record_context = bind_record_context(
        context=context,
        batch_id=batch_id,
        raw_record=raw_record,
    )

    try:
        return await build_transform_success_outcome(
            context=record_context,
            transform=transform,
            raw_record=raw_record,
            index=index,
            normalization_processor=normalization_processor,
            gold_filter=gold_filter,
            gold_transform=gold_transform,
            dq_config=dq_config,
            debug_export_service=debug_export_service,
        )
    except FilteredOutError as error:
        return handle_filtered_out_error(
            error,
            _build_filtered_out_handling_context_from_mapping(locals()),
        )
    except TRANSFORM_PROCESSING_ERRORS as error:
        return handle_transform_processing_error(
            error,
            context=record_context,
            batch_id=batch_id,
            raw_record=raw_record,
            index=index,
            error_classifier=error_classifier,
            batch_metrics=batch_metrics,
            dq_config=dq_config,
            debug_export_service=debug_export_service,
        )
