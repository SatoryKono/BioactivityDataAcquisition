"""Canonical submodule for batch-transformer state helpers."""

from __future__ import annotations

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

__all__ = _state.__all__
