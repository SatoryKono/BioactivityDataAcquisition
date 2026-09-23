"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Sequence

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.sorted_governance_targets import (
    _governance_policy_specs,
    _sorted_governance_targets,
)

__all__ = [
    "_governance_policy_targets",
]


def _governance_policy_targets(
    snapshot: GraphSnapshot,
    *,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> tuple[tuple[NodeKey, tuple[Sequence[NodeKey], ...]], ...]:
    sorted_ports, sorted_adapters, sorted_pipelines, sorted_contracts = (
        _sorted_governance_targets(
            port_nodes=port_nodes,
            adapter_nodes=adapter_nodes,
            pipeline_nodes=pipeline_nodes,
            contract_nodes=contract_nodes,
        )
    )
    return tuple(
        _governance_policy_specs(
            snapshot,
            sorted_ports=sorted_ports,
            sorted_adapters=sorted_adapters,
            sorted_pipelines=sorted_pipelines,
            sorted_contracts=sorted_contracts,
        )
    )
