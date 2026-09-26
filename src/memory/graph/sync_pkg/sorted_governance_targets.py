"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Sequence

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.governance_policy_definitions import (
    _governance_policy_definitions,
    _governance_policy_spec,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_governance_policy_specs",
    "_sorted_governance_targets",
]


def _sorted_governance_targets(
    *,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey], list[NodeKey]]:
    return (
        sorted(port_nodes, key=lambda node: node.name),
        sorted(adapter_nodes.values(), key=lambda node: node.name),
        sorted(pipeline_nodes.values(), key=lambda node: node.name),
        sorted(contract_nodes.values(), key=lambda node: node.name),
    )


def _governance_policy_specs(
    snapshot: GraphSnapshot,
    *,
    sorted_ports: list[NodeKey],
    sorted_adapters: list[NodeKey],
    sorted_pipelines: list[NodeKey],
    sorted_contracts: list[NodeKey],
) -> list[tuple[NodeKey, tuple[Sequence[NodeKey], ...]]]:
    return [
        _governance_policy_spec(*policy)
        for policy in _governance_policy_definitions(
            snapshot,
            sorted_ports=sorted_ports,
            sorted_adapters=sorted_adapters,
            sorted_pipelines=sorted_pipelines,
            sorted_contracts=sorted_contracts,
        )
    ]
