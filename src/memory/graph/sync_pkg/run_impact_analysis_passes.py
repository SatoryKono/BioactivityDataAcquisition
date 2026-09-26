"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_pipeline_test_edges import _add_pipeline_test_edges
from memory.graph.sync_pkg.alert_runbook_context import _add_pipeline_operational_edges
from memory.graph.sync_pkg.alert_runbook_path import _add_governance_edges
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _add_pipeline_normalization_edges,
)
from memory.graph.sync_pkg.extract_code_duplication_surfaces import (
    _extract_code_duplication_surfaces,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_composite_pipeline_dependencies import (
    _add_pipeline_normalization_evidence,
)
from memory.graph.sync_pkg.provider_regression_provider_target import (
    _add_alert_surfaces,
)

__all__ = [
    "_run_impact_analysis_passes",
]


def _run_impact_analysis_passes(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    memory_mapping: dict[str, object],
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    _add_pipeline_normalization_edges(snapshot, pipeline_nodes, memory_mapping)
    _add_pipeline_normalization_evidence(snapshot, pipeline_nodes)
    _add_pipeline_test_edges(snapshot, root, pipeline_nodes, memory_mapping)
    _add_alert_surfaces(
        snapshot, root, project, today, pipeline_nodes, contract_nodes, memory_mapping
    )
    _add_governance_edges(
        snapshot, port_nodes, adapter_nodes, pipeline_nodes, contract_nodes
    )
    _add_pipeline_operational_edges(snapshot, pipeline_nodes, memory_mapping)
    _extract_code_duplication_surfaces(snapshot, root, project, today, memory_mapping)
