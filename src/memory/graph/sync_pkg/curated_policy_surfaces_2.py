"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.curated_policy_surfaces import CURATED_POLICY_SURFACES
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.policysurfacecontext import (
    _link_policy_governance_targets,
    _policy_surface_context,
)

__all__ = [
    "_add_policy_surface_entry",
    "_curated_policy_surfaces",
]


def _curated_policy_surfaces() -> tuple[dict[str, object], ...]:
    return tuple(CURATED_POLICY_SURFACES)


def _add_policy_surface_entry(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    policy_payload: dict[str, object],
) -> None:
    policy_context = _policy_surface_context(snapshot, policy_payload, today)
    policy = policy_context.policy
    snapshot.add_relation(
        project, "HAS_POLICY_SURFACE", policy, provenance="curated_policy"
    )
    snapshot.add_relation(
        policy, "BACKED_BY", policy_context.artifact, provenance="curated_policy"
    )
    _link_policy_governance_targets(snapshot, policy, policy_payload)
