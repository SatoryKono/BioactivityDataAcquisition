"""Internal helper functions for batch transformation orchestration."""

from __future__ import annotations

import asyncio
import time

from bioetl.application.core.batch_transformer_attempts import (
    bind_record_context,
    transform_record_attempt,
)
from bioetl.application.core.batch_transformer_quarantine import (
    flush_dq_records,
    flush_filtered_records,
    route_single_transform_attempt,
)
from bioetl.application.core.batch_transformer_state import (
    RecordTransformOutcome,
    TransformAggregationState,
    TransformedRecord,
    TransformResult,
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
    "bind_record_context",
    "build_transform_result",
    "create_transform_aggregation_state",
    "flush_dq_records",
    "flush_filtered_records",
    "route_single_transform_attempt",
    "transform_record_attempt",
    "yield_control_if_needed",
]


YIELD_INTERVAL_SECONDS = 0.5


async def yield_control_if_needed(last_yield_at: float) -> float:
    """Cooperatively yield to the event loop during CPU-heavy transforms."""
    now = time.monotonic()
    if now - last_yield_at < YIELD_INTERVAL_SECONDS:
        return last_yield_at
    await asyncio.sleep(0)
    return time.monotonic()
