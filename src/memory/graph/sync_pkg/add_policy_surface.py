"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_policy_artifact",
    "_add_policy_surface",
]


def _add_policy_surface(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "policy_surface",
        str(policy_payload["name"]),
        summary=str(policy_payload["summary"]),
        source_path=str(policy_payload["source_path"]),
        source_kind="repo_policy_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_policy_artifact(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> NodeKey:
    source_path = str(policy_payload["source_path"])
    return snapshot.add_node(
        str(policy_payload["artifact_label"]),
        source_path,
        summary=str(policy_payload["summary"]),
        source_path=source_path,
        source_kind="policy_artifact",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
