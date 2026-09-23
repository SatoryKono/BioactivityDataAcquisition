"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _optional_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.runtime_state_properties import (
    _link_runtime_state_evidence_dependencies,
    _link_runtime_state_workflow_dependency,
)

__all__ = [
    "_link_runtime_state_dependencies",
    "_link_runtime_state_run_and_pipeline",
]


def _link_runtime_state_run_and_pipeline(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    manifest_id = _optional_text(spec.get("manifest_id"))
    if manifest_id is not None:
        run_key = NodeKey("run_instance_surface", manifest_id)
        if run_key in snapshot.nodes:
            snapshot.add_relation(
                run_key, "HAS_RUNTIME_STATE", state, provenance="runtime_state"
            )
            pipeline_name = _optional_text(
                snapshot.nodes[run_key].properties.get("pipeline_name")
            )
            if pipeline_name is not None:
                pipeline_key = NodeKey("pipeline_surface", pipeline_name)
                if pipeline_key in snapshot.nodes:
                    snapshot.add_relation(
                        state, "DEPENDS_ON", pipeline_key, provenance="runtime_state"
                    )


def _link_runtime_state_dependencies(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_state_workflow_dependency(snapshot, state, spec)
    _link_runtime_state_evidence_dependencies(snapshot, state, spec)
