"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.run_instance_doc_targets import (
    _run_instance_artifact_targets,
    _run_instance_doc_targets,
)
from memory.graph.sync_pkg.run_instance_properties import (
    _link_run_instance_contract_dependency,
    _link_run_instance_pipeline_dependency,
)
from memory.graph.sync_pkg.runtime_state_properties import _runtime_state_properties

__all__ = [
    "_add_runtime_state_surface",
    "_link_run_instance_artifacts",
    "_link_run_instance_dependencies",
    "_link_run_instance_documents",
]


def _link_run_instance_dependencies(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_run_instance_pipeline_dependency(snapshot, surface, spec)
    _link_run_instance_contract_dependency(snapshot, surface, spec)


def _link_run_instance_documents(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    for doc_key in _run_instance_doc_targets(spec):
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "DESCRIBED_IN", doc_key, provenance="runtime_evidence"
            )


def _link_run_instance_artifacts(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    for artifact_key in _run_instance_artifact_targets(spec):
        if artifact_key in snapshot.nodes:
            snapshot.add_relation(
                surface,
                "REFERENCES_ARTIFACT",
                artifact_key,
                provenance="runtime_evidence",
            )


def _add_runtime_state_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> NodeKey:
    state = snapshot.add_node(
        "runtime_state_surface",
        str(spec["name"]),
        summary=f"Deterministic runtime state surface `{spec['name']}`.",
        **_runtime_state_properties(spec),
        source_kind="runtime_state_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUNTIME_STATE", state, provenance="runtime_state"
    )
    return state
