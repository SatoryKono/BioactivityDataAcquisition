"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.governance_policy_targets import _governance_policy_targets
from memory.graph.sync_pkg.governance_target_groups import _link_policy_governance_group
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_alert_runbook_doc",
    "_add_governance_edges",
    "_alert_runbook_path",
]


def _alert_runbook_path(root: Path, annotations: dict[str, object]) -> str | None:
    runbook = annotations.get("runbook")
    if not isinstance(runbook, str):
        return None
    return runbook if (root / runbook).is_file() else None


def _add_alert_runbook_doc(
    snapshot: GraphSnapshot,
    alert_name: str,
    runbook: str,
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "doc_artifact",
        runbook,
        summary=f"Runbook referenced by alert `{alert_name}`.",
        source_path=runbook,
        source_kind="alert_runbook",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_governance_edges(
    snapshot: GraphSnapshot,
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
) -> None:
    for policy, target_groups in _governance_policy_targets(
        snapshot,
        port_nodes=port_nodes,
        adapter_nodes=adapter_nodes,
        pipeline_nodes=pipeline_nodes,
        contract_nodes=contract_nodes,
    ):
        _link_policy_governance_group(snapshot, policy, *target_groups)
