"""Batch and stream orchestration loops for batch transformation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from bioetl.application.core.transformer_runtime.state import (
    RecordTransformOutcome,
    TransformAggregationState,
    TransformedRecord,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    create_transform_aggregation_state,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord

TransformLoopResult = TypeVar(
    "TransformLoopResult",
    RecordTransformOutcome,
    TransformedRecord,
)

YIELD_INTERVAL_SECONDS = 0.5


async def yield_control_if_needed(last_yield_at: float) -> float:
    """Cooperatively yield to the event loop during CPU-heavy transforms."""
    now = time.monotonic()
    if now - last_yield_at < YIELD_INTERVAL_SECONDS:
        return last_yield_at
    await asyncio.sleep(0)
    return time.monotonic()


async def _collect_transform_state[
    TransformLoopResult: (RecordTransformOutcome, TransformedRecord)
](
    *,
    records: list[BronzeRecord],
    batch_id: BatchID,
    start_index: int,
    transform_record: Callable[
        [BronzeRecord, BatchID, int],
        Awaitable[TransformLoopResult],
    ],
    apply_result: Callable[
        [TransformAggregationState, TransformLoopResult],
        None,
    ],
    yield_control: Callable[[float], Awaitable[float]],
) -> TransformAggregationState:
    """Run a transform loop and accumulate state for batch or streaming mode."""
    state = create_transform_aggregation_state()
    last_yield_at = time.monotonic()
    for index, raw_record in enumerate(records, start=start_index):
        last_yield_at = await yield_control(last_yield_at)
        result = await transform_record(raw_record, batch_id, index)
        apply_result(state, result)
    return state


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
    return await _collect_transform_state(
        records=records,
        batch_id=batch_id,
        start_index=start_index,
        transform_record=transform_attempt,
        apply_result=lambda state, result: apply_transform_outcome_to_state(
            state=state,
            attempt=result,
        ),
        yield_control=yield_control,
    )


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
    return await _collect_transform_state(
        records=records,
        batch_id=batch_id,
        start_index=start_index,
        transform_record=transform_single,
        apply_result=lambda state, result: apply_stream_transform_result_to_state(
            state=state,
            result=result,
        ),
        yield_control=yield_control,
    )


__all__ = [
    "YIELD_INTERVAL_SECONDS",
    "collect_batch_transform_state",
    "collect_stream_transform_state",
    "yield_control_if_needed",
]
