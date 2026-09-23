"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_runtime_state_evidence_materials import (
    _link_runtime_state_evidence_materials,
)
from memory.graph.sync_pkg.link_runtime_state_run_and_pipeline import (
    _link_runtime_state_dependencies,
    _link_runtime_state_run_and_pipeline,
)

__all__ = [
    "_link_runtime_state_surface",
]


def _link_runtime_state_surface(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_state_run_and_pipeline(snapshot, state, spec)
    _link_runtime_state_dependencies(snapshot, state, spec)
    _link_runtime_state_evidence_materials(snapshot, state, spec)
