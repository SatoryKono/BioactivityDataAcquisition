"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import json
import sys

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.batch_pipeline_names import (
    _batch_pipeline_names,
    _normalization_progress_payload,
)
from memory.graph.sync_pkg.normalization_evidence_statement import (
    _NORMALIZATION_EVIDENCE_STATEMENT,
    _normalization_statement_params,
)

__all__ = [
    "_emit_normalization_apply_progress",
    "_normalization_batch_pipeline_span",
    "_normalization_statement",
]


def _normalization_statement(
    pipeline_name: str,
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    return {
        "statement": _NORMALIZATION_EVIDENCE_STATEMENT,
        "parameters": _normalization_statement_params(pipeline_name, evidence),
    }


def _normalization_batch_pipeline_span(
    batch: list[dict[str, JsonValue]],
) -> tuple[str | None, str | None]:
    pipeline_names = _batch_pipeline_names(batch)
    if not pipeline_names:
        return None, None
    return pipeline_names[0], pipeline_names[-1]


def _emit_normalization_apply_progress(
    *,
    event: str,
    batch_index: int,
    batch_count: int,
    statement_count: int,
    pipeline_start: str | None,
    pipeline_end: str | None,
    elapsed_seconds: float | None = None,
) -> None:
    payload = _normalization_progress_payload(
        event=event,
        batch_index=batch_index,
        batch_count=batch_count,
        statement_count=statement_count,
        pipeline_start=pipeline_start,
        pipeline_end=pipeline_end,
        elapsed_seconds=elapsed_seconds,
    )
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.stderr.flush()
