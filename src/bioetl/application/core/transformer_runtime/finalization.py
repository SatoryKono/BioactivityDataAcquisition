"""Canonical submodule for batch-transformer finalization helpers."""

from __future__ import annotations

from bioetl.application.core.batch_transformer_dq_thresholds import (
    DQThresholdCheckResult,
    ThresholdBreach,
    ThresholdBreachReason,
    check_dq_thresholds,
    classify_dq_threshold_breach,
    compute_error_rate,
    resolve_threshold_value,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_batch_transform_result,
    finalize_stream_transform_result,
)

__all__ = [
    "DQThresholdCheckResult",
    "ThresholdBreach",
    "ThresholdBreachReason",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "compute_error_rate",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
    "resolve_threshold_value",
]
