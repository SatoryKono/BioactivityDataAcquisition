"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_ast import (
    _dataframe_model_class_names,
    _imported_repo_modules,
)
from memory.graph.sync_pkg._core_convert import _rel_path, _resolve_repo_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import _resolve_python_module_surface

__all__ = [
    "_contract_source_resolved_path",
    "_link_contract_imported_modules",
    "_link_contract_source_module",
    "_update_contract_schema_classes",
]


def _contract_source_resolved_path(context: ContractEntryContext) -> Path | None:
    source_path = context.raw_entry.get("source_path")
    if not isinstance(source_path, str):
        return None
    return _resolve_repo_path(context.root, context.registry_path, source_path)


def _update_contract_schema_classes(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
) -> None:
    schema_classes = _dataframe_model_class_names(resolved)
    if schema_classes:
        snapshot.add_node(
            "contract_surface", context.contract_ref, schema_classes=schema_classes
        )


def _link_contract_source_module(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
) -> None:
    module_key = NodeKey("module_surface", _rel_path(context.root, resolved))
    if module_key in snapshot.nodes:
        snapshot.add_relation(
            context.contract, "BACKED_BY", module_key, provenance="impact_contracts"
        )


def _link_contract_imported_modules(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    resolved: Path,
    source_prefixes: tuple[str, ...],
) -> None:
    for imported_module in sorted(_imported_repo_modules(resolved, source_prefixes)):
        dependency_key = _resolve_python_module_surface(context.root, imported_module)
        if dependency_key is not None and dependency_key in snapshot.nodes:
            snapshot.add_relation(
                context.contract,
                "DEPENDS_ON",
                dependency_key,
                provenance="impact_contracts",
            )
