"""Per-record transform helpers for batch transformation."""

from __future__ import annotations

from inspect import isawaitable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
)
from bioetl.domain.behavior.dq_rule_evaluator import (
    evaluate_dq_rules_for_record,
    select_highest_priority_disposition,
)
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.types import BronzeRecord
from bioetl.domain.types.dq_contracts import DQDisposition

if TYPE_CHECKING:
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID, ErrorType

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


def _empty_outcome() -> RecordTransformOutcome:
    """Return an empty transform outcome."""
    return RecordTransformOutcome(silver_record=None, gold_record=None)


def _finalize_transformed_record(
    *,
    transformed: dict[str, object] | PreSilverRecord | None,
    normalization_processor: RecordNormalizationProcessor | None,
    context: PipelineContext,
    index: int,
) -> dict[str, object] | None:
    """Finalize transform output through the normalization stage."""
    if transformed is None:
        return None
    if isinstance(transformed, PreSilverRecord):
        if normalization_processor is None:
            raise RuntimeError("PreSilverRecord requires RecordNormalizationProcessor")
        finalized_record: dict[str, object] | None = (
            normalization_processor.finalize_pre_silver(
                transformed,
                context,
                index,
            )
        )
        return finalized_record
    if normalization_processor is None:
        return transformed
    normalized_record: dict[str, object] | None = (
        normalization_processor.normalize_record(transformed)
    )
    return normalized_record


def _build_gold_record(
    *,
    context: PipelineContext,
    silver_record: dict[str, object],
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
) -> dict[str, object] | None:
    """Create a Gold record when the finalized Silver record passes filtering."""
    if not gold_filter(context, silver_record):
        return None
    gold_record = cast(
        dict[str, object] | None,
        gold_transform(context, silver_record),
    )
    return gold_record


def _resolve_invalid_record_policy(dq_config: DQConfig | None) -> str:
    """Resolve invalid-record policy with runtime-safe default."""
    if dq_config is None:
        return "quarantine"
    return dq_config.invalid_record_policy


def _apply_runtime_dq_outcomes(
    *,
    silver_record: dict[str, object],
    dq_config: DQConfig | None,
) -> dict[str, object]:
    """Evaluate runtime DQ rules and project non-blocking flags onto one record."""
    outcomes = evaluate_dq_rules_for_record(silver_record, dq_config)
    if not outcomes:
        return silver_record

    strongest_disposition = select_highest_priority_disposition(outcomes)
    if strongest_disposition in (
        DQDisposition.QUARANTINE,
        DQDisposition.SKIP,
        DQDisposition.FAIL,
    ):
        violated_rules = ", ".join(outcome.rule_id for outcome in outcomes)
        raise DataQualityError(
            "Runtime DQ validation failed: "
            f"disposition={strongest_disposition.value}; rules=[{violated_rules}]"
        )

    projected = dict(silver_record)
    if any(outcome.disposition == DQDisposition.WARN for outcome in outcomes):
        projected["_dq_warn"] = True
    if any(
        outcome.disposition == DQDisposition.WARN and outcome.severity == "error"
        for outcome in outcomes
    ):
        projected["_dq_error"] = True
    return projected


def _transform_failure_entity_id(raw_record: BronzeRecord) -> object:
    """Resolve the best-effort entity identifier for transform failure logs."""
    return (
        raw_record.get("publication_id")
        or raw_record.get("document_chembl_id")
        or raw_record.get("activity_id")
    )


def _log_transform_record_failure(
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
    index: int,
    error: Exception,
) -> None:
    """Emit a structured transform-failure log with record context."""
    context.logger.exception(
        "transform_record_failed",
        pipeline=context.pipeline_name,
        batch_id=str(batch_id),
        record_index=index,
        source_batch_id=str(context.source_batch_id)
        if context.source_batch_id is not None
        else None,
        error_type=type(error).__name__,
        error=str(error),
        entity_id=_transform_failure_entity_id(raw_record),
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
        return await _build_transform_success_outcome(
            context=record_context,
            transform=transform,
            raw_record=raw_record,
            index=index,
            normalization_processor=normalization_processor,
            gold_filter=gold_filter,
            gold_transform=gold_transform,
            dq_config=dq_config,
        )
    except FilteredOutError as error:
        return _handle_filtered_out_error(
            error,
            batch_metrics=batch_metrics,
            dq_config=dq_config,
            raw_record=raw_record,
        )
    except TRANSFORM_PROCESSING_ERRORS as error:
        return _handle_transform_processing_error(
            error,
            context=record_context,
            batch_id=batch_id,
            raw_record=raw_record,
            index=index,
            error_classifier=error_classifier,
            batch_metrics=batch_metrics,
            dq_config=dq_config,
        )


async def _build_transform_success_outcome(
    *,
    context: PipelineContext,
    transform: TransformCallback,
    raw_record: BronzeRecord,
    index: int,
    normalization_processor: RecordNormalizationProcessor | None,
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
    dq_config: DQConfig | None,
) -> RecordTransformOutcome:
    transformed = await _resolve_transform_result(transform(context, raw_record, index))
    finalized_record = _finalize_transformed_record(
        transformed=transformed,
        normalization_processor=normalization_processor,
        context=context,
        index=index,
    )
    if finalized_record is None:
        return _empty_outcome()
    finalized_record = _apply_runtime_dq_outcomes(
        silver_record=finalized_record,
        dq_config=dq_config,
    )
    gold_record = _build_gold_record(
        context=context,
        silver_record=finalized_record,
        gold_filter=gold_filter,
        gold_transform=gold_transform,
    )
    return RecordTransformOutcome(
        silver_record=finalized_record,
        gold_record=gold_record,
    )


async def _resolve_transform_result(
    transformed_result: dict[str, object] | PreSilverRecord | None | object,
) -> dict[str, object] | PreSilverRecord | None:
    if isawaitable(transformed_result):
        return cast(
            dict[str, object] | PreSilverRecord | None,
            await transformed_result,
        )
    return cast(dict[str, object] | PreSilverRecord | None, transformed_result)


def _handle_filtered_out_error(
    error: FilteredOutError,
    *,
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
    raw_record: BronzeRecord,
) -> RecordTransformOutcome:
    batch_metrics.track_processed_records("filtered_out", 1)
    batch_metrics.track_silver_filter_rejection(error.details or None)
    policy = _resolve_invalid_record_policy(dq_config)
    if policy == "skip":
        return _empty_outcome()
    if policy == "fail":
        raise error
    return RecordTransformOutcome(
        silver_record=None,
        gold_record=None,
        filtered_entry=FilteredQuarantineEntry(
            record=raw_record,
            reason=str(error),
            details=error.details or None,
        ),
    )


def _handle_transform_processing_error(
    error: Exception,
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
    index: int,
    error_classifier: ErrorClassifier,
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
) -> RecordTransformOutcome:
    _log_transform_record_failure(
        context=context,
        batch_id=batch_id,
        raw_record=raw_record,
        index=index,
        error=error,
    )
    error_type = error_classifier.classify(error)
    if not error_type.is_data_quality():
        raise error
    return _handle_data_quality_transform_error(
        error,
        error_type=error_type,
        batch_metrics=batch_metrics,
        dq_config=dq_config,
        raw_record=raw_record,
    )


def _handle_data_quality_transform_error(
    error: Exception,
    *,
    error_type: ErrorType,
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
    raw_record: BronzeRecord,
) -> RecordTransformOutcome:
    batch_metrics.track_error("transform", error_type)
    policy = _resolve_invalid_record_policy(dq_config)
    if policy == "fail":
        raise error
    if policy == "skip":
        return _empty_outcome()
    batch_metrics.track_quarantined_records(error_type, 1)
    return RecordTransformOutcome(
        silver_record=None,
        gold_record=None,
        dq_entry=DQQuarantineEntry(raw_record, error_type, str(error)),
    )
