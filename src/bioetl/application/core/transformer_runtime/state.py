"""Canonical submodule for batch-transformer state helpers."""

from __future__ import annotations
# ruff: noqa: I001

from bioetl.application.core.batch_transformer_state import (
    RecordTransformOutcome as RecordTransformOutcome,
    TransformAggregationState as TransformAggregationState,
    TransformResult as TransformResult,
    TransformedRecord as TransformedRecord,
    accumulate_stream_transform_result as accumulate_stream_transform_result,
    accumulate_transform_outcome as accumulate_transform_outcome,
    apply_stream_transform_result_to_state as apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state as apply_transform_outcome_to_state,
    build_transform_result as build_transform_result,
    create_transform_aggregation_state as create_transform_aggregation_state,
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
