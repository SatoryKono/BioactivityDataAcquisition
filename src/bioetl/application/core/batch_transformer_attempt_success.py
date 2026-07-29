"""Successful record-transform attempt helpers."""

from __future__ import annotations

from inspect import isawaitable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.filtering import FilterDecision

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
    from bioetl.domain.types import BronzeRecord


def empty_outcome() -> RecordTransformOutcome:
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
) -> tuple[dict[str, object] | None, bool, object | None]:
    """Create a Gold record and report contract-based exclusion."""
    if not gold_filter(context, silver_record):
        return None, True, _resolve_gold_filter_details(gold_filter, silver_record)
    gold_record = cast(
        dict[str, object] | None,
        gold_transform(context, silver_record),
    )
    return gold_record, False, None


def _resolve_gold_filter_details(
    gold_filter: GoldFilterCallback,
    record: dict[str, object],
) -> dict[str, object] | None:
    owner = getattr(gold_filter, "__self__", None)
    gold_filters = getattr(owner, "_gold_filters", None)
    evaluate = getattr(gold_filters, "evaluate", None)
    if not callable(evaluate):
        return None
    decision = evaluate(record)
    if isinstance(decision, FilterDecision) and not decision.include:
        return decision.to_dict()
    return None


def _apply_runtime_dq_outcomes(
    *,
    silver_record: dict[str, object],
    dq_config: DQConfig | None,
) -> dict[str, object]:
    """Evaluate runtime DQ rules and project non-blocking flags onto one record."""
    if dq_config is None:
        return silver_record
    from bioetl.domain.behavior.dq_rule_evaluator import (
        evaluate_dq_rules_for_record,
        select_highest_priority_disposition,
    )
    from bioetl.domain.types.dq_contracts import DQDisposition

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


async def build_transform_success_outcome(
    *,
    context: PipelineContext,
    transform: TransformCallback,
    raw_record: BronzeRecord,
    index: int,
    normalization_processor: RecordNormalizationProcessor | None,
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
    dq_config: DQConfig | None,
    debug_export_service: DebugExportService | None,
) -> RecordTransformOutcome:
    """Build the outcome for a successfully transformed record."""
    transformed = await resolve_transform_result(transform(context, raw_record, index))
    finalized_record = _finalize_transformed_record(
        transformed=transformed,
        normalization_processor=normalization_processor,
        context=context,
        index=index,
    )
    if finalized_record is None:
        return empty_outcome()
    finalized_record = _apply_runtime_dq_outcomes(
        silver_record=finalized_record,
        dq_config=dq_config,
    )
    gold_record, gold_excluded_by_contract, gold_filter_details = _build_gold_record(
        context=context,
        silver_record=finalized_record,
        gold_filter=gold_filter,
        gold_transform=gold_transform,
    )
    if debug_export_service is not None:
        debug_export_service.record_transform_success(
            raw_record=raw_record,
            record_index=index,
            silver_record=finalized_record,
            gold_record=gold_record,
            gold_excluded_by_contract=gold_excluded_by_contract,
            gold_filter_details=gold_filter_details,
        )
    return RecordTransformOutcome(
        silver_record=finalized_record,
        gold_record=gold_record,
        gold_excluded_by_contract=gold_excluded_by_contract,
    )


async def resolve_transform_result(
    transformed_result: dict[str, object] | PreSilverRecord | None | object,
) -> dict[str, object] | PreSilverRecord | None:
    """Await transform output when needed and normalize the static type."""
    if isawaitable(transformed_result):
        return cast(
            dict[str, object] | PreSilverRecord | None,
            await transformed_result,
        )
    return cast(dict[str, object] | PreSilverRecord | None, transformed_result)


__all__ = [
    "build_transform_success_outcome",
    "empty_outcome",
    "resolve_transform_result",
]
