"""Canonical grouping for batch-transformer runtime helpers."""

from __future__ import annotations

from bioetl.application.core.transformer_runtime.attempts import (
    TRANSFORM_PROCESSING_ERRORS,
    bind_record_context,
    transform_record_attempt,
)
from bioetl.application.core.transformer_runtime.finalization import (
    ThresholdBreach,
    check_dq_thresholds,
    classify_dq_threshold_breach,
    compute_error_rate,
    finalize_batch_transform_result,
    finalize_stream_transform_result,
)
from bioetl.application.core.transformer_runtime.orchestration import (
    YIELD_INTERVAL_SECONDS,
    collect_batch_transform_state,
    collect_stream_transform_state,
    yield_control_if_needed,
)
from bioetl.application.core.transformer_runtime.quarantine import (
    QUARANTINE_WRITE_WARN_ONLY_ERRORS,
    flush_dq_records,
    flush_filtered_records,
    route_single_transform_attempt,
)
from bioetl.application.core.transformer_runtime.state import (
    RecordTransformOutcome,
    TransformAggregationState,
    TransformResult,
    TransformedRecord,
    accumulate_stream_transform_result,
    accumulate_transform_outcome,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    build_transform_result,
    create_transform_aggregation_state,
)
from bioetl.application.core.transformer_runtime.streaming import (
    StreamingBatchProcessor,
)

__all__ = [
    "QUARANTINE_WRITE_WARN_ONLY_ERRORS",
    "RecordTransformOutcome",
    "StreamingBatchProcessor",
    "TRANSFORM_PROCESSING_ERRORS",
    "ThresholdBreach",
    "TransformAggregationState",
    "TransformResult",
    "TransformedRecord",
    "YIELD_INTERVAL_SECONDS",
    "accumulate_stream_transform_result",
    "accumulate_transform_outcome",
    "apply_stream_transform_result_to_state",
    "apply_transform_outcome_to_state",
    "bind_record_context",
    "build_transform_result",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "collect_batch_transform_state",
    "collect_stream_transform_state",
    "compute_error_rate",
    "create_transform_aggregation_state",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
    "flush_dq_records",
    "flush_filtered_records",
    "route_single_transform_attempt",
    "transform_record_attempt",
    "yield_control_if_needed",
]
