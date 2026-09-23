"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import ContractMappingConfig, NodeKey
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _add_contract_entry_surface,
)
from memory.graph.sync_pkg.contract_registry_payload import _link_contract_dependencies
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_register_contract_entry",
]


def _register_contract_entry(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    registry_artifact: NodeKey,
    *,
    contract_ref: str,
    raw_entry: dict[str, object],
    today: str,
    mapping_config: ContractMappingConfig,
    contract_nodes: dict[str, NodeKey],
) -> None:
    entry_context = _add_contract_entry_surface(
        snapshot,
        root,
        project,
        registry_artifact,
        contract_ref=contract_ref,
        raw_entry=raw_entry,
        today=today,
    )
    contract_nodes[contract_ref] = entry_context.contract
    _link_contract_dependencies(snapshot, entry_context, mapping_config)
