"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_dashboard_surface import _add_dashboard_surface
from memory.graph.sync_pkg.default_batch_size import DOC_GRAFANA_DASHBOARDS_JSON
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_dashboard_graph",
    "_composite_dependency_target",
    "_link_config_artifact",
]


def _composite_dependency_target(
    dependency_pipeline: object,
    entity_nodes: dict[str, NodeKey],
) -> NodeKey | None:
    if isinstance(dependency_pipeline, str) and dependency_pipeline in entity_nodes:
        return entity_nodes[dependency_pipeline]
    return None


def _link_config_artifact(
    snapshot: GraphSnapshot,
    target: NodeKey,
    *,
    path: str,
    summary: str,
    source_kind: str,
    today: str,
    provenance: str,
) -> None:
    artifact = snapshot.add_node(
        "config_artifact",
        path,
        summary=summary,
        source_path=path,
        source_kind=source_kind,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(target, "DEFINED_BY", artifact, provenance=provenance)


def _add_dashboard_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    dashboards_root = root / "grafana" / "dashboards"
    source_surface = NodeKey("doc_source_surface", DOC_GRAFANA_DASHBOARDS_JSON)
    snapshot.add_relation(
        project, "HAS_DOC_SOURCE_SURFACE", source_surface, provenance="dashboard_graph"
    )
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        dashboard = _add_dashboard_surface(snapshot, root, dashboard_path, today)
        snapshot.add_relation(
            project, "HAS_DASHBOARD", dashboard, provenance="dashboard_graph"
        )
        snapshot.add_relation(
            source_surface,
            "IS_FACTUAL_SOURCE_FOR",
            dashboard,
            provenance="dashboard_graph",
        )
