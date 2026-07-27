"""Canonical submodule for batch-transformer finalization helpers."""

from __future__ import annotations

from bioetl.application.core import batch_transformer_dq_thresholds as _dq_thresholds
from bioetl.application.core.batch_transformer_finalization import (
    finalize_batch_transform_result,
    finalize_stream_transform_result,
)

# Re-export DQ threshold helpers without re-listing the same literal ``__all__``
# barrel that lives in ``batch_transformer_dq_thresholds`` (pylint R0801).
DQThresholdCheckResult = _dq_thresholds.DQThresholdCheckResult
ThresholdBreach = _dq_thresholds.ThresholdBreach
ThresholdBreachReason = _dq_thresholds.ThresholdBreachReason
check_dq_thresholds = _dq_thresholds.check_dq_thresholds
classify_dq_threshold_breach = _dq_thresholds.classify_dq_threshold_breach
compute_error_rate = _dq_thresholds.compute_error_rate
resolve_threshold_value = _dq_thresholds.resolve_threshold_value

__all__ = [
    *list(_dq_thresholds.__all__),
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
]
