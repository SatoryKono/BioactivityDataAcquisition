"""Canonical submodule for batch-transformer finalization helpers."""

from __future__ import annotations
# ruff: noqa: I001

from bioetl.application.core.batch_transformer_dq_thresholds import (
    DQThresholdCheckResult as DQThresholdCheckResult,
    ThresholdBreach as ThresholdBreach,
    ThresholdBreachReason as ThresholdBreachReason,
    check_dq_thresholds as check_dq_thresholds,
    classify_dq_threshold_breach as classify_dq_threshold_breach,
    compute_error_rate as compute_error_rate,
    resolve_threshold_value as resolve_threshold_value,
)
from bioetl.application.core.batch_transformer_dq_thresholds import (
    __all__ as _DQ_ALL,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_batch_transform_result as finalize_batch_transform_result,
    finalize_stream_transform_result as finalize_stream_transform_result,
)

__all__ = [
    *_DQ_ALL,
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
]
