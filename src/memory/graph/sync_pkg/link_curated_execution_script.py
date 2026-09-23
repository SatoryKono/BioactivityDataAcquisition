"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_curated_cluster_readme import (
    _add_curated_cluster_entrypoint,
    _add_curated_cluster_execution,
    _add_curated_cluster_readme,
)
from memory.graph.sync_pkg.curated_script_clusters import CURATED_SCRIPT_CLUSTERS
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_curated_script_clusters",
    "_link_curated_execution_script",
]


def _link_curated_execution_script(
    snapshot: GraphSnapshot,
    execution: NodeKey,
    execution_payload: dict[str, object],
    *,
    today: str,
    dev_readme: NodeKey,
) -> None:
    script_path = execution_payload.get("script_path")
    if not isinstance(script_path, str):
        return
    script = snapshot.add_node(
        "script_surface",
        script_path,
        summary=f"Script surface for `{script_path}`.",
        source_path=script_path,
        source_kind="script_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(script, "PROVIDES", execution, provenance="curated_execution")
    if script_path.startswith("scripts/engineering/dev/"):
        snapshot.add_relation(
            dev_readme, "DESCRIBES", execution, provenance="scripts_dev_readme"
        )


def _add_curated_script_clusters(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    for cluster in CURATED_SCRIPT_CLUSTERS:
        readme = _add_curated_cluster_readme(snapshot, cluster, today)
        snapshot.add_relation(
            project, "HAS_DOC_ARTIFACT", readme, provenance="curated_scripts"
        )
        entrypoint = _add_curated_cluster_entrypoint(snapshot, cluster, today)

        for execution_payload in _as_iterable(cluster.get("execution_paths")):
            if not isinstance(execution_payload, dict):
                continue
            _add_curated_cluster_execution(
                snapshot,
                today,
                entrypoint,
                readme,
                execution_payload,
            )
