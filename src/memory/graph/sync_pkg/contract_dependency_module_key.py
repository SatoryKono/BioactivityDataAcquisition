"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _add_contract_doc_dependency,
    _contract_dependency_doc_path,
)
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_contract_dependency_module_key",
    "_link_contract_dependency_module",
    "_link_contract_doc_dependencies",
]


def _contract_dependency_module_key(root: Path, module_path: str) -> NodeKey | None:
    resolved_module = root / module_path
    if not resolved_module.is_file():
        return None
    return NodeKey("module_surface", _rel_path(root, resolved_module))


def _link_contract_dependency_module(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    module_path: str,
    provenance: str,
) -> None:
    module_key = _contract_dependency_module_key(context.root, module_path)
    if module_key is not None and module_key in snapshot.nodes:
        snapshot.add_relation(
            context.contract, "DEPENDS_ON", module_key, provenance=provenance
        )


def _link_contract_doc_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    doc_paths: list[str],
    anchor_fields: list[str],
    *,
    summary: str,
    source_kind: str,
    provenance: str,
) -> None:
    for doc_path in doc_paths:
        resolved_doc = _contract_dependency_doc_path(
            context.root, doc_path, anchor_fields
        )
        if resolved_doc is None:
            continue
        artifact = _add_contract_doc_dependency(
            snapshot,
            context=context,
            doc_path=doc_path,
            summary=summary,
            source_kind=source_kind,
        )
        snapshot.add_relation(
            context.contract, "DESCRIBED_IN", artifact, provenance=provenance
        )
