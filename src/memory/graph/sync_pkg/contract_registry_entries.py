"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contract_mapping_config import _contract_mapping_config
from memory.graph.sync_pkg.contract_registry_payload import _contract_registry_payload
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_contract_provider import _add_contract_registry_artifact
from memory.graph.sync_pkg.register_contract_entry import _register_contract_entry

__all__ = [
    "_add_contract_surfaces",
    "_contract_registry_entries",
]


def _contract_registry_entries(root: Path) -> dict[str, dict[str, object]]:
    return {
        contract_ref: raw_entry
        for contract_ref, raw_entry in sorted(_contract_registry_payload(root).items())
        if isinstance(contract_ref, str) and isinstance(raw_entry, dict)
    }


def _add_contract_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> dict[str, NodeKey]:
    registry_artifact = _add_contract_registry_artifact(snapshot, root, today)
    if registry_artifact is None:
        return {}
    entries = _contract_registry_entries(root)
    if not entries:
        return {}
    mapping_config = _contract_mapping_config(memory_mapping)

    contract_nodes: dict[str, NodeKey] = {}
    for contract_ref, raw_entry in entries.items():
        _register_contract_entry(
            snapshot,
            root,
            project,
            registry_artifact,
            contract_ref=contract_ref,
            raw_entry=raw_entry,
            today=today,
            mapping_config=mapping_config,
            contract_nodes=contract_nodes,
        )

    return contract_nodes
