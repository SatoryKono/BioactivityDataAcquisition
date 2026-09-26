"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import time

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.apply_runtime import _batched
from memory.graph.sync_pkg.emit_normalization_batch_progress import (
    _emit_normalization_batch_progress,
    _normalization_batch_summary,
)
from memory.graph.sync_pkg.normalization_statement import (
    _normalization_batch_pipeline_span,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

__all__ = [
    "_execute_normalization_evidence_batch",
    "_normalization_evidence_batches",
]


def _normalization_evidence_batches(
    statements: list[dict[str, JsonValue]],
    batch_size: int,
) -> list[list[dict[str, JsonValue]]]:
    return _batched(statements, batch_size)


def _execute_normalization_evidence_batch(
    client: Neo4jHttpClient,
    batch: list[dict[str, JsonValue]],
    *,
    batch_index: int,
    batch_count: int,
) -> dict[str, JsonValue]:
    pipeline_start, pipeline_end = _normalization_batch_pipeline_span(batch)
    _emit_normalization_batch_progress(
        event="batch_start",
        batch=batch,
        batch_index=batch_index,
        batch_count=batch_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
    )
    batch_started = time.perf_counter()
    client.execute(
        batch,
        context=(
            "normalization evidence batch "
            f"{batch_index}/{batch_count} "
            f"pipelines {pipeline_start or '?'}..{pipeline_end or '?'}"
        ),
    )
    batch_elapsed = time.perf_counter() - batch_started
    _emit_normalization_batch_progress(
        event="batch_complete",
        batch=batch,
        batch_index=batch_index,
        batch_count=batch_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=batch_elapsed,
    )
    return _normalization_batch_summary(
        batch=batch,
        batch_index=batch_index,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=batch_elapsed,
    )
