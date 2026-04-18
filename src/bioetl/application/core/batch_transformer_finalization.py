"""Batch transformer finalization helpers and DQ threshold checking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from numbers import Real
from typing import TYPE_CHECKING

from bioetl.application.core.batch_transformer_state import build_transform_result
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import BatchTransformContext
    from bioetl.application.core.transformer_runtime.state import BatchTransformState
    from bioetl.domain.config.pipeline import TransformConfig


from bioetl.application.core.batch_transformer_state import TransformResult


class ThresholdBreachReason(Enum):
    """Classification of DQ threshold breaches."""

    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class DQThresholdCheckResult:
    """Result of DQ threshold validation."""

    breach: ThresholdBreachReason
    error_rate: float
    soft_threshold: float | None
    hard_threshold: float | None


async def finalize_batch_transform_result(
    *,
    context: BatchTransformContext,
    config: TransformConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: BatchTransformState,
    records: list[BronzeRecord],
    flush_filtered_records: callable,
    flush_dq_records: callable,
) -> TransformResult:
    """Finalize one batch result with DQ checks and quarantine flushing."""
    dq_config = getattr(config, "dq_config", None) or getattr(config, "dq", None)
    soft_threshold = _resolve_threshold_value(
        dq_config,
        "soft_threshold",
        "soft_fail_threshold",
    )
    hard_threshold = _resolve_threshold_value(
        dq_config,
        "hard_threshold",
        "hard_fail_threshold",
    )
    error_count = _resolve_error_count(batch_metrics=batch_metrics, state=state)

    threshold_result = check_dq_thresholds(
        error_count=error_count,
        record_count=len(records),
        soft_threshold=soft_threshold,
        hard_threshold=hard_threshold,
    )

    if threshold_result.breach == ThresholdBreachReason.HARD:
        context.logger.error(
            "DQ hard threshold exceeded",
            error_rate=threshold_result.error_rate,
            soft_threshold=threshold_result.soft_threshold,
            hard_threshold=threshold_result.hard_threshold,
            error_count=error_count,
            record_count=len(records),
        )
        batch_metrics.track_dq_validation_failure(
            stage="threshold",
            severity="hard_fail",
        )
        raise DataQualityThresholdError(
            error_rate=threshold_result.error_rate,
            threshold=float(threshold_result.hard_threshold),
        )

    if threshold_result.breach == ThresholdBreachReason.SOFT:
        context.logger.warning(
            "DQ threshold breach detected",
            breach=threshold_result.breach.value,
            error_rate=threshold_result.error_rate,
            soft_threshold=threshold_result.soft_threshold,
            hard_threshold=threshold_result.hard_threshold,
            error_count=error_count,
            record_count=len(records),
        )
        batch_metrics.track_dq_validation_failure(
            stage="threshold",
            severity="soft_fail",
        )

    state.records_quarantine_failed += await _await_flush_count(flush_filtered_records)
    state.records_quarantine_failed += await _await_flush_count(flush_dq_records)
    return build_transform_result(state)


async def finalize_stream_transform_result(
    *,
    context: BatchTransformContext,
    config: TransformConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: BatchTransformState,
    records: list[BronzeRecord],
    flush_filtered_records: callable,
    flush_dq_records: callable,
) -> TransformResult:
    """Finalize one streaming result via the shared batch finalizer."""
    return await finalize_batch_transform_result(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        state=state,
        records=records,
        flush_filtered_records=flush_filtered_records,
        flush_dq_records=flush_dq_records,
    )


def check_dq_thresholds(
    *,
    error_count: int,
    record_count: int,
    soft_threshold: float | None,
    hard_threshold: float | None,
) -> DQThresholdCheckResult:
    """Check whether the current error rate breaches configured thresholds."""
    if record_count == 0:
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.NONE,
            error_rate=0.0,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )

    error_rate = error_count / record_count

    if hard_threshold is not None and error_rate >= float(hard_threshold):
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.HARD,
            error_rate=error_rate,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )

    if soft_threshold is not None and error_rate >= float(soft_threshold):
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.SOFT,
            error_rate=error_rate,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )

    return DQThresholdCheckResult(
        breach=ThresholdBreachReason.NONE,
        error_rate=error_rate,
        soft_threshold=soft_threshold,
        hard_threshold=hard_threshold,
    )


def classify_dq_threshold_breach(
    error_rate: float,
    soft_threshold: float | None,
    hard_threshold: float | None,
) -> ThresholdBreachReason:
    """Classify the threshold breach for a concrete error rate."""
    if hard_threshold is not None and error_rate >= hard_threshold:
        return ThresholdBreachReason.HARD

    if soft_threshold is not None and error_rate >= soft_threshold:
        return ThresholdBreachReason.SOFT

    return ThresholdBreachReason.NONE


ThresholdBreach = ThresholdBreachReason


def compute_error_rate(error_count: int, record_count: int) -> float:
    """Compute the error rate, guarding the zero-record case."""
    return error_count / record_count if record_count > 0 else 0.0


def _resolve_threshold_value(
    dq_config: object | None,
    *attribute_names: str,
) -> float | None:
    """Resolve one numeric threshold while ignoring loose mocks."""
    if dq_config is None:
        return None
    for attribute_name in attribute_names:
        value = getattr(dq_config, attribute_name, None)
        if isinstance(value, Real) and not isinstance(value, bool):
            return float(value)
    return None


def _resolve_error_count(
    *,
    batch_metrics: BatchMetricsRecorderService,
    state: BatchTransformState,
) -> int:
    """Resolve a concrete DQ error count without trusting mock placeholders."""
    error_count = getattr(batch_metrics, "error_count", None)
    if isinstance(error_count, int) and not isinstance(error_count, bool):
        return error_count
    return state.quarantined_count


async def _await_flush_count(flush_callback: callable) -> int:
    """Await one flush callback and coerce absent counts to zero."""
    flushed = await flush_callback()
    return flushed if isinstance(flushed, int) and not isinstance(flushed, bool) else 0


__all__ = [
    "DQThresholdCheckResult",
    "ThresholdBreach",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "compute_error_rate",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
]
