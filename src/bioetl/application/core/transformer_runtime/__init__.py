"""Canonical grouping for batch-transformer runtime helpers."""

from __future__ import annotations

# ruff: noqa: I001

from bioetl.application.core.transformer_runtime.attempts import (
    TRANSFORM_PROCESSING_ERRORS as TRANSFORM_PROCESSING_ERRORS,
    bind_record_context as bind_record_context,
    transform_record_attempt as transform_record_attempt,
)
from bioetl.application.core.transformer_runtime.finalization import (
    DQThresholdCheckResult as DQThresholdCheckResult,
    ThresholdBreach as ThresholdBreach,
    ThresholdBreachReason as ThresholdBreachReason,
    check_dq_thresholds as check_dq_thresholds,
    classify_dq_threshold_breach as classify_dq_threshold_breach,
    compute_error_rate as compute_error_rate,
    finalize_batch_transform_result as finalize_batch_transform_result,
    finalize_stream_transform_result as finalize_stream_transform_result,
    resolve_threshold_value as resolve_threshold_value,
)
from bioetl.application.core.transformer_runtime.orchestration import (
    YIELD_INTERVAL_SECONDS as YIELD_INTERVAL_SECONDS,
    collect_batch_transform_state as collect_batch_transform_state,
    collect_stream_transform_state as collect_stream_transform_state,
    yield_control_if_needed as yield_control_if_needed,
)
from bioetl.application.core.transformer_runtime.quarantine import (
    QUARANTINE_WRITE_WARN_ONLY_ERRORS as QUARANTINE_WRITE_WARN_ONLY_ERRORS,
    flush_dq_records as flush_dq_records,
    flush_filtered_records as flush_filtered_records,
    route_single_transform_attempt as route_single_transform_attempt,
)
from bioetl.application.core.transformer_runtime import state as _state
from bioetl.application.core.transformer_runtime.streaming import (
    StreamingBatchProcessor as StreamingBatchProcessor,
)
from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade,
)

_STATE_EXPORTS = {name: (_state.__name__, name) for name in _state.__all__}
install_lazy_export_facade(globals(), __name__, _STATE_EXPORTS)

__all__ = [
    "QUARANTINE_WRITE_WARN_ONLY_ERRORS",
    "TRANSFORM_PROCESSING_ERRORS",
    "YIELD_INTERVAL_SECONDS",
    "DQThresholdCheckResult",
    "StreamingBatchProcessor",
    "ThresholdBreach",
    "ThresholdBreachReason",
    "bind_record_context",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "collect_batch_transform_state",
    "collect_stream_transform_state",
    "compute_error_rate",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
    "flush_dq_records",
    "flush_filtered_records",
    "resolve_threshold_value",
    "route_single_transform_attempt",
    "transform_record_attempt",
    "yield_control_if_needed",
    *_state.__all__,
]
