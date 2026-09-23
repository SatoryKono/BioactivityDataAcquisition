"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_policy_surface import (
    _add_policy_artifact,
    _add_policy_surface,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.policy_governance_targets import _policy_governance_targets

__all__ = [
    "PolicySurfaceContext",
    "_link_policy_governance_targets",
    "_policy_surface_context",
]


@dataclass(frozen=True)
class PolicySurfaceContext:
    policy: NodeKey
    artifact: NodeKey


def _policy_surface_context(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> PolicySurfaceContext:
    return PolicySurfaceContext(
        policy=_add_policy_surface(snapshot, policy_payload, today),
        artifact=_add_policy_artifact(snapshot, policy_payload, today),
    )


def _link_policy_governance_targets(
    snapshot: GraphSnapshot,
    policy: NodeKey,
    policy_payload: dict[str, object],
) -> None:
    for target in _policy_governance_targets(policy_payload):
        snapshot.add_relation(policy, "GOVERNS", target, provenance="curated_policy")
