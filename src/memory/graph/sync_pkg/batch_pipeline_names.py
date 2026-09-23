"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from datetime import UTC, datetime

from memory.graph.sync_pkg._core_convert import _as_mapping
from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_batch_pipeline_names",
    "_normalization_progress_payload",
]


def _batch_pipeline_names(batch: list[dict[str, JsonValue]]) -> list[str]:
    return [
        str(pipeline_name)
        for statement in batch
        for pipeline_name in [
            _as_mapping(statement.get("parameters")).get("pipeline_name")
        ]
        if isinstance(pipeline_name, str) and pipeline_name
    ]


def _normalization_progress_payload(
    *,
    event: str,
    batch_index: int,
    batch_count: int,
    statement_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None,
) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "event": event,
        "sync_scope": "normalization_evidence_only",
        "batch_index": batch_index,
        "batch_count": batch_count,
        "statement_count": statement_count,
        "pipeline_start": pipeline_start,
        "pipeline_end": pipeline_end,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(elapsed_seconds, 3)
    return payload
