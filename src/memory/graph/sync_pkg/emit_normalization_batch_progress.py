"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.normalization_statement import (
    _emit_normalization_apply_progress,
)

__all__ = [
    "_emit_normalization_batch_progress",
    "_normalization_batch_summary",
]


def _emit_normalization_batch_progress(
    *,
    event: str,
    batch: list[dict[str, JsonValue]],
    batch_index: int,
    batch_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None = None,
) -> None:
    _emit_normalization_apply_progress(
        event=event,
        batch_index=batch_index,
        batch_count=batch_count,
        statement_count=len(batch),
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=elapsed_seconds,
    )


def _normalization_batch_summary(
    *,
    batch: list[dict[str, JsonValue]],
    batch_index: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float,
) -> dict[str, JsonValue]:
    return {
        "batch_index": batch_index,
        "statement_count": len(batch),
        "pipeline_start": pipeline_start,
        "pipeline_end": pipeline_end,
        "elapsed_seconds": round(elapsed_seconds, 3),
    }
