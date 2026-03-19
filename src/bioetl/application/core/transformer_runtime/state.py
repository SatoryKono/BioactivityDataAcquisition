"""Canonical submodule for batch-transformer state helpers."""

from __future__ import annotations

from bioetl.application.core.batch_transformer_state import (
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

__all__ = [
    "RecordTransformOutcome",
    "TransformAggregationState",
    "TransformResult",
    "TransformedRecord",
    "accumulate_stream_transform_result",
    "accumulate_transform_outcome",
    "apply_stream_transform_result_to_state",
    "apply_transform_outcome_to_state",
    "build_transform_result",
    "create_transform_aggregation_state",
]
