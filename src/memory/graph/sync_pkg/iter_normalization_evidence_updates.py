"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.composite_pipeline_dependency_keys import (
    _build_normalization_pipeline_evidence,
)
from memory.graph.sync_pkg.default_batch_size import DEFAULT_BATCH_SIZE
from memory.graph.sync_pkg.normalization_evidence_batches import (
    _execute_normalization_evidence_batch,
    _normalization_evidence_batches,
)
from memory.graph.sync_pkg.normalization_evidence_update_payload import (
    _normalization_evidence_update_payload,
)
from memory.graph.sync_pkg.normalization_statement import _normalization_statement
from memory.graph.sync_pkg.transport import Neo4jHttpClient, resolve_neo4j_connection

__all__ = [
    "_iter_normalization_evidence_updates",
    "_normalization_evidence_statements",
    "apply_normalization_evidence_only",
]


def _iter_normalization_evidence_updates(
    pipeline_nodes: dict[str, NodeKey],
    evidence_by_pipeline: dict[str, dict[str, JsonValue]],
) -> tuple[tuple[str, NodeKey, dict[str, JsonValue]], ...]:
    updates: list[tuple[str, NodeKey, dict[str, JsonValue]]] = []
    for pipeline_name, evidence in evidence_by_pipeline.items():
        if pipeline_nodes.get(pipeline_name) is None:
            continue
        updates.append(
            (
                pipeline_name,
                NodeKey("entity_config", pipeline_name),
                _normalization_evidence_update_payload(evidence),
            )
        )
    return tuple(updates)


def _normalization_evidence_statements() -> list[dict[str, JsonValue]]:
    evidence_by_pipeline = _build_normalization_pipeline_evidence()
    statements: list[dict[str, JsonValue]] = []
    for pipeline_name, evidence in sorted(evidence_by_pipeline.items()):
        statements.append(_normalization_statement(pipeline_name, evidence))
    return statements


def apply_normalization_evidence_only(
    root: Path,
    http_uri: str | None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, JsonValue]:
    started_at = datetime.now(tz=UTC).isoformat()
    overall_started = time.perf_counter()
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    evidence_started = time.perf_counter()
    statements = _normalization_evidence_statements()
    evidence_build_seconds = time.perf_counter() - evidence_started
    batches = _normalization_evidence_batches(statements, batch_size)
    batch_summaries: list[dict[str, JsonValue]] = []
    completed_statement_count = 0

    for batch_index, batch in enumerate(batches, start=1):
        batch_summary = _execute_normalization_evidence_batch(
            client,
            batch,
            batch_index=batch_index,
            batch_count=len(batches),
        )
        completed_statement_count += len(batch)
        batch_summaries.append(batch_summary)

    total_seconds = time.perf_counter() - overall_started
    return {
        "started_at": started_at,
        "pipeline_count": len(statements),
        "batch_count": len(batches),
        "batch_size": batch_size,
        "completed_statement_count": completed_statement_count,
        "evidence_build_seconds": round(evidence_build_seconds, 3),
        "total_seconds": round(total_seconds, 3),
        "batches": batch_summaries,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
