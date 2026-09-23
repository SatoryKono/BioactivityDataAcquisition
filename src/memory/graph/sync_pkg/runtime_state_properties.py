"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import (
    _as_iterable,
    _coerce_int,
    _optional_text,
)
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_runtime_state_evidence_dependencies",
    "_link_runtime_state_workflow_dependency",
    "_runtime_state_properties",
]


def _runtime_state_properties(spec: dict[str, object]) -> dict[str, object]:
    return {
        "manifest_id": _optional_text(spec.get("manifest_id")),
        "state_kind": _optional_text(spec.get("state_kind")),
        "state_status": _optional_text(spec.get("state_status")),
        "retry_count": _coerce_int(spec["retry_count"])
        if isinstance(spec.get("retry_count"), int)
        else None,
        "retry_strategy": _optional_text(spec.get("retry_strategy")),
        "lock_key": _optional_text(spec.get("lock_key")),
        "lock_scope": _optional_text(spec.get("lock_scope")),
        "owner_hint": _optional_text(spec.get("owner_hint")),
        "workflow_name": _optional_text(spec.get("workflow_name")),
    }


def _link_runtime_state_workflow_dependency(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    workflow_name = _optional_text(spec.get("workflow_name"))
    if workflow_name is None:
        return
    workflow_key = NodeKey("workflow_surface", workflow_name)
    if workflow_key in snapshot.nodes:
        snapshot.add_relation(
            state, "DEPENDS_ON", workflow_key, provenance="runtime_state"
        )


def _link_runtime_state_evidence_dependencies(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    for evidence_name in _as_iterable(spec.get("runtime_evidence_refs")):
        evidence_key = NodeKey("runtime_evidence_surface", str(evidence_name))
        if evidence_key in snapshot.nodes:
            snapshot.add_relation(
                state, "DEPENDS_ON", evidence_key, provenance="runtime_state"
            )
