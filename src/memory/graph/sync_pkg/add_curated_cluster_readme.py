"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_execution_path_node,
    _link_execution_gate,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_curated_cluster_entrypoint",
    "_add_curated_cluster_execution",
    "_add_curated_cluster_readme",
]


def _add_curated_cluster_readme(
    snapshot: GraphSnapshot,
    cluster: dict[str, object],
    today: str,
) -> NodeKey:
    readme_path = str(cluster["readme_path"])
    return snapshot.add_node(
        "doc_artifact",
        readme_path,
        summary=str(cluster["readme_summary"]),
        source_path=readme_path,
        source_kind="ops_doc",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_cluster_entrypoint(
    snapshot: GraphSnapshot,
    cluster: dict[str, object],
    today: str,
) -> NodeKey:
    entrypoint_path = str(cluster["entrypoint_path"])
    return snapshot.add_node(
        "script_surface",
        entrypoint_path,
        summary=str(cluster["entrypoint_summary"]),
        source_path=entrypoint_path,
        source_kind="script_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_cluster_execution(
    snapshot: GraphSnapshot,
    today: str,
    entrypoint: NodeKey,
    readme: NodeKey,
    execution_payload: dict[str, object],
) -> None:
    execution = _add_execution_path_node(snapshot, today, execution_payload)
    snapshot.add_relation(
        entrypoint, "PROVIDES", execution, provenance="curated_script_clusters"
    )
    snapshot.add_relation(
        readme, "DESCRIBES", execution, provenance="curated_script_clusters"
    )
    _link_execution_gate(
        snapshot,
        execution,
        execution_payload,
        provenance="curated_script_clusters",
    )
