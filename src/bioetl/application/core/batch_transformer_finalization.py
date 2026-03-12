"""Finalization and threshold helpers for batch transformation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.batch_transformer_state import (
    TransformAggregationState,
    TransformResult,
    build_transform_result,
)
from bioetl.domain.exceptions import DataQualityThresholdError

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord

ThresholdBreach = Literal["none", "soft_fail", "hard_fail"]


def compute_error_rate(
    *,
    total_count: int,
    quarantined_count: int,
) -> float:
    """Compute the quarantine rate for DQ threshold evaluation."""
    if total_count <= 0:
        return 0.0
    return quarantined_count / total_count


def classify_dq_threshold_breach(
    *,
    dq_config: DQConfig | None,
    error_rate: float,
) -> ThresholdBreach:
    """Classify the strongest DQ threshold breach for the current batch."""
    if dq_config is None:
        return "none"

    if (
        dq_config.hard_fail_threshold
        and dq_config.hard_fail_threshold < 1.0
        and error_rate >= dq_config.hard_fail_threshold
    ):
        return "hard_fail"

    if (
        dq_config.soft_fail_threshold
        and error_rate >= dq_config.soft_fail_threshold
    ):
        return "soft_fail"

    return "none"


def check_dq_thresholds(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    records: list[BronzeRecord],
    quarantined_count: int,
) -> None:
    """Check DQ thresholds and raise or warn as appropriate."""
    if not records:
        return

    total_count = len(records)
    error_rate = compute_error_rate(
        total_count=total_count,
        quarantined_count=quarantined_count,
    )
    dq_config = config.dq_config
    breach = classify_dq_threshold_breach(
        dq_config=dq_config,
        error_rate=error_rate,
    )

    if breach == "none" or dq_config is None:
        return

    batch_metrics.track_dq_validation_failure(
        stage="transform",
        severity=breach,
    )

    if breach == "hard_fail":
        raise DataQualityThresholdError(error_rate, dq_config.hard_fail_threshold)

    context.logger.warning(
        "DQ Soft Threshold exceeded",
        error_rate=round(error_rate, 4),
        threshold=dq_config.soft_fail_threshold,
        quarantined_count=quarantined_count,
        total_count=total_count,
        hard_threshold=dq_config.hard_fail_threshold,
        pipeline=config.pipeline_name,
    )


def finalize_stream_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
) -> TransformResult:
    """Validate streaming thresholds and build result."""
    check_dq_thresholds(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        records=records,
        quarantined_count=state.quarantined_count,
    )
    return build_transform_result(state)


async def finalize_batch_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
    flush_filtered_records: Callable[[], Awaitable[int]],
    flush_dq_records: Callable[[], Awaitable[int]],
) -> TransformResult:
    """Flush quarantine buffers, validate thresholds, and build result."""
    filtered_failed = await flush_filtered_records()
    dq_failed = await flush_dq_records()

    check_dq_thresholds(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        records=records,
        quarantined_count=state.quarantined_count,
    )
    state.records_quarantine_failed = filtered_failed + dq_failed
    return build_transform_result(state)
