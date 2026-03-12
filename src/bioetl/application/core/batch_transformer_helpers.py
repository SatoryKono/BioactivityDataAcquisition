"""Compatibility facade for batch transformation helper primitives."""

from __future__ import annotations

from bioetl.application.core import batch_transformer_attempts as _attempts
from bioetl.application.core import batch_transformer_orchestration as _orchestration
from bioetl.application.core import batch_transformer_quarantine as _quarantine
from bioetl.application.core import batch_transformer_state as _state

RecordTransformOutcome = _state.RecordTransformOutcome
TransformAggregationState = _state.TransformAggregationState
TransformResult = _state.TransformResult
TransformedRecord = _state.TransformedRecord
accumulate_stream_transform_result = _state.accumulate_stream_transform_result
accumulate_transform_outcome = _state.accumulate_transform_outcome
apply_stream_transform_result_to_state = _state.apply_stream_transform_result_to_state
apply_transform_outcome_to_state = _state.apply_transform_outcome_to_state
build_transform_result = _state.build_transform_result
create_transform_aggregation_state = _state.create_transform_aggregation_state
bind_record_context = _attempts.bind_record_context
transform_record_attempt = _attempts.transform_record_attempt
flush_dq_records = _quarantine.flush_dq_records
flush_filtered_records = _quarantine.flush_filtered_records
route_single_transform_attempt = _quarantine.route_single_transform_attempt
YIELD_INTERVAL_SECONDS = _orchestration.YIELD_INTERVAL_SECONDS
yield_control_if_needed = _orchestration.yield_control_if_needed

__all__ = [
    "RecordTransformOutcome",
    "TransformAggregationState",
    "TransformResult",
    "TransformedRecord",
    "accumulate_stream_transform_result",
    "accumulate_transform_outcome",
    "apply_stream_transform_result_to_state",
    "apply_transform_outcome_to_state",
    "bind_record_context",
    "build_transform_result",
    "create_transform_aggregation_state",
    "flush_dq_records",
    "flush_filtered_records",
    "route_single_transform_attempt",
    "transform_record_attempt",
    "yield_control_if_needed",
]
