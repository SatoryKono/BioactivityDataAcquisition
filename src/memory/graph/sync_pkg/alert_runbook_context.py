"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import AlertRunbookContext, NodeKey
from memory.graph.sync_pkg.alert_runbook_path import _alert_runbook_path
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_operational_context import (
    _pipeline_operational_context,
)
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    _link_pipeline_operational_for_pipeline,
    _sorted_pipeline_nodes,
)

__all__ = [
    "_add_pipeline_operational_edges",
    "_alert_runbook_context",
]


def _alert_runbook_context(
    root: Path,
    annotations: dict[str, object],
) -> AlertRunbookContext | None:
    runbook = _alert_runbook_path(root, annotations)
    if runbook is None:
        return None
    return AlertRunbookContext(runbook=runbook)


def _add_pipeline_operational_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    operational_context = _pipeline_operational_context(memory_mapping)
    for pipeline in _sorted_pipeline_nodes(pipeline_nodes):
        _link_pipeline_operational_for_pipeline(
            snapshot,
            pipeline,
            operational_context=operational_context,
        )
