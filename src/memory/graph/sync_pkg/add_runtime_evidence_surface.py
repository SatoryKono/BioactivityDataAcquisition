"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _link_run_instance_artifacts,
    _link_run_instance_dependencies,
    _link_run_instance_documents,
)
from memory.graph.sync_pkg.link_runtime_evidence_support import (
    _add_runtime_evidence_storage_refs,
    _link_runtime_evidence_support,
)

__all__ = [
    "_add_runtime_evidence_surface",
    "_link_run_instance_surface",
]


def _add_runtime_evidence_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> None:
    evidence_name = str(spec["name"])
    surface = snapshot.add_node(
        "runtime_evidence_surface",
        evidence_name,
        summary=str(spec["summary"]),
        source_path=str(spec["source_path"]),
        source_kind="runtime_evidence_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUNTIME_EVIDENCE", surface, provenance="runtime_evidence"
    )
    _link_runtime_evidence_support(snapshot, surface, spec)
    _add_runtime_evidence_storage_refs(
        snapshot,
        project,
        surface,
        evidence_name=evidence_name,
        storage_refs=spec["storage_refs"],
        today=today,
    )


def _link_run_instance_surface(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_run_instance_dependencies(snapshot, surface, spec)
    _link_run_instance_documents(snapshot, surface, spec)
    _link_run_instance_artifacts(snapshot, surface, spec)
