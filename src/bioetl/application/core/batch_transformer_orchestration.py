"""Batch and stream orchestration loops for batch transformation."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.application.core.batch_transformer_state import (
    RecordTransformOutcome,
    TransformAggregationState,
    TransformedRecord,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    create_transform_aggregation_state,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord


async def collect_batch_transform_state(
    *,
    records: list[BronzeRecord],
    batch_id: BatchID,
    start_index: int,
    transform_attempt: Callable[
        [BronzeRecord, BatchID, int],
        Awaitable[RecordTransformOutcome],
    ],
    yield_control: Callable[[float], Awaitable[float]],
) -> TransformAggregationState:
    """Transform all batch records and accumulate batch state."""
    state = create_transform_aggregation_state()
    last_yield_at = time.monotonic()

    for index, raw_record in enumerate(records, start=start_index):
        last_yield_at = await yield_control(last_yield_at)
        attempt = await transform_attempt(raw_record, batch_id, index)
        apply_transform_outcome_to_state(
            state=state,
            attempt=attempt,
        )

    return state


async def collect_stream_transform_state(
    *,
    records: list[BronzeRecord],
    batch_id: BatchID,
    start_index: int,
    transform_single: Callable[
        [BronzeRecord, BatchID, int],
        Awaitable[TransformedRecord],
    ],
    yield_control: Callable[[float], Awaitable[float]],
) -> TransformAggregationState:
    """Transform all records in streaming mode and accumulate state."""
    state = create_transform_aggregation_state()
    last_yield_at = time.monotonic()

    for index, raw_record in enumerate(records, start=start_index):
        last_yield_at = await yield_control(last_yield_at)
        result = await transform_single(raw_record, batch_id, index)
        apply_stream_transform_result_to_state(
            state=state,
            result=result,
        )

    return state
