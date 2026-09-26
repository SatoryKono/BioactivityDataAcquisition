"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.runtime_state_artifact_targets import (
    _runtime_state_artifact_targets,
    _runtime_state_doc_targets,
)

__all__ = [
    "_link_runtime_state_evidence_materials",
]


def _link_runtime_state_evidence_materials(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    for artifact_key in _runtime_state_artifact_targets(spec):
        if artifact_key in snapshot.nodes:
            snapshot.add_relation(
                state, "REFERENCES_ARTIFACT", artifact_key, provenance="runtime_state"
            )
    for doc_key in _runtime_state_doc_targets(spec):
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                state, "DESCRIBED_IN", doc_key, provenance="runtime_state"
            )
