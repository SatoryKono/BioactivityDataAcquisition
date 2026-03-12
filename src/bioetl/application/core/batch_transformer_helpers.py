"""Internal helper functions for batch transformation orchestration."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from bioetl.application.core.batch_transformer_attempts import (
    bind_record_context,
    transform_record_attempt,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_finalization import (
    check_dq_thresholds as _check_dq_thresholds,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_batch_transform_result as _finalize_batch_transform_result,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_stream_transform_result as _finalize_stream_transform_result,
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
from bioetl.application.core.quarantine_manager import (
    QuarantineManagerService,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BatchID


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
    "check_dq_thresholds",
    "create_transform_aggregation_state",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
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


async def finalize_batch_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    quarantine_manager: QuarantineManagerService,
    state: TransformAggregationState,
    batch_id: BatchID,
    records: list[BronzeRecord],
) -> TransformResult:
    """Flush batch quarantine buffers, validate thresholds, and build result."""
    return await _finalize_batch_transform_result(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        state=state,
        records=records,
        flush_filtered_records=lambda: flush_filtered_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=state.filtered_records,
            batch_id=batch_id,
        ),
        flush_dq_records=lambda: flush_dq_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=state.dq_records,
            batch_id=batch_id,
        ),
    )


def finalize_stream_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
) -> TransformResult:
    """Validate streaming thresholds and build result."""
    return _finalize_stream_transform_result(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        state=state,
        records=records,
    )


def check_dq_thresholds(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    records: list[BronzeRecord],
    quarantined_count: int,
) -> None:
    """Check DQ thresholds and raise or warn as appropriate."""
    _check_dq_thresholds(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        records=records,
        quarantined_count=quarantined_count,
    )
