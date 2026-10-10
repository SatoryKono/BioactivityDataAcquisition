"""Canonical submodule for batch-transformer finalization helpers."""

from __future__ import annotations

from bioetl.application.core import batch_transformer_dq_thresholds as _dq
from bioetl.application.core import batch_transformer_finalization as _finalization

DQThresholdCheckResult = _dq.DQThresholdCheckResult
ThresholdBreach = _dq.ThresholdBreach
ThresholdBreachReason = _dq.ThresholdBreachReason
check_dq_thresholds = _dq.check_dq_thresholds
classify_dq_threshold_breach = _dq.classify_dq_threshold_breach
compute_error_rate = _dq.compute_error_rate
resolve_threshold_value = _dq.resolve_threshold_value
finalize_batch_transform_result = _finalization.finalize_batch_transform_result
finalize_stream_transform_result = _finalization.finalize_stream_transform_result

__all__ = [
    *_dq.__all__,
    *_finalization.__all__,
]
