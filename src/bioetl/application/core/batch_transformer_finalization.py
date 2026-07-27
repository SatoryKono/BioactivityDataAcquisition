"""Batch transformer finalization helpers and DQ threshold checking."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from bioetl.application.core.batch_transformer_state import (
    TransformAggregationState,
    TransformResult,
    build_transform_result,
)
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.application.core.batch_transformer_dq_thresholds import (
    DQThresholdCheckResult,
    ThresholdBreach,
    ThresholdBreachReason,
    check_dq_thresholds,
    classify_dq_threshold_breach,
    compute_error_rate,
    resolve_threshold_value,
)


class _BatchTransformContext(Protocol):
    """Minimal transform context surface needed by finalization helpers."""

    @property
    def logger(self) -> LoggerPort: ...


class _TransformConfig(Protocol):
    """Loose transform config surface exposing DQ configuration."""

    @property
    def dq_config(self) -> object | None: ...


class _BatchMetricsRecorderService(Protocol):
    """Minimal batch-metrics surface needed by finalization helpers."""

    @property
    def error_count(self) -> int | None: ...

    def track_dq_validation_failure(self, *, stage: str, severity: str) -> None: ...


FlushCountCallback = Callable[[], Awaitable[object]]


async def finalize_batch_transform_result(
    *,
    context: _BatchTransformContext,
    config: _TransformConfig,
    batch_metrics: _BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
    flush_filtered_records: FlushCountCallback,
    flush_dq_records: FlushCountCallback,
) -> TransformResult:
    """Finalize one batch result with DQ checks and quarantine flushing."""
    dq_config = config.dq_config
    soft_threshold = resolve_threshold_value(
        dq_config,
        "soft_threshold",
        "soft_fail_threshold",
    )
    hard_threshold = resolve_threshold_value(
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
        assert threshold_result.hard_threshold is not None
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
            threshold=threshold_result.hard_threshold,
        )

    if threshold_result.breach == ThresholdBreachReason.SOFT:
        context.logger.warning(
            "DQ Soft Threshold exceeded",
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
    context: _BatchTransformContext,
    config: _TransformConfig,
    batch_metrics: _BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
    flush_filtered_records: FlushCountCallback,
    flush_dq_records: FlushCountCallback,
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

def _resolve_error_count(
    *,
    batch_metrics: _BatchMetricsRecorderService,
    state: TransformAggregationState,
) -> int:
    """Resolve a concrete DQ error count without trusting mock placeholders."""
    error_count = getattr(batch_metrics, "error_count", None)
    if isinstance(error_count, int) and not isinstance(error_count, bool):
        return error_count
    return state.quarantined_count


async def _await_flush_count(flush_callback: FlushCountCallback) -> int:
    """Await one flush callback and coerce absent counts to zero."""
    flushed = await flush_callback()
    return flushed if isinstance(flushed, int) and not isinstance(flushed, bool) else 0


__all__ = [
    "DQThresholdCheckResult",
    "ThresholdBreach",
    "ThresholdBreachReason",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "compute_error_rate",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
]
