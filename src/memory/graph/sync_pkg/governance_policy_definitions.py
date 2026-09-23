"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Sequence

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.governance_target_groups import (
    _alert_surface_nodes,
    _governance_target_groups,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_governance_policy_definitions",
    "_governance_policy_spec",
]


def _governance_policy_definitions(
    snapshot: GraphSnapshot,
    *,
    sorted_ports: list[NodeKey],
    sorted_adapters: list[NodeKey],
    sorted_pipelines: list[NodeKey],
    sorted_contracts: list[NodeKey],
) -> tuple[tuple[str, Sequence[NodeKey], Sequence[NodeKey] | None], ...]:
    return (
        ("hexagonal import matrix", sorted_ports, sorted_adapters),
        ("hexagonal package layout", sorted_ports, sorted_adapters),
        ("pipeline assembly model", sorted_pipelines, None),
        ("medallion storage contract", sorted_contracts, sorted_pipelines),
        ("observability surface model", _alert_surface_nodes(snapshot), None),
    )


def _governance_policy_spec(
    policy_name: str,
    target_group: Sequence[NodeKey],
    extra_target_group: Sequence[NodeKey] | None = None,
) -> tuple[NodeKey, tuple[Sequence[NodeKey], ...]]:
    return NodeKey("policy_surface", policy_name), _governance_target_groups(
        target_group,
        extra_target_group,
    )
