"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _rel_path, _resolve_repo_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _link_contract_dependency_module,
)
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_contract_module_dependencies",
    "_published_contract_artifact_key",
    "_published_contract_artifact_paths",
]


def _published_contract_artifact_paths(
    context: ContractEntryContext,
) -> tuple[str, ...]:
    published_artifacts = context.raw_entry.get("published_artifacts")
    if not isinstance(published_artifacts, list):
        return ()
    return tuple(path for path in published_artifacts if isinstance(path, str))


def _published_contract_artifact_key(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    published_path: str,
) -> NodeKey | None:
    resolved = _resolve_repo_path(context.root, context.registry_path, published_path)
    if resolved is None:
        return None
    relative_path = _rel_path(context.root, resolved)
    return snapshot.add_node(
        "doc_artifact",
        relative_path,
        summary=f"Published contract artifact for `{context.contract_ref}`.",
        source_path=relative_path,
        source_kind="published_contract",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_contract_module_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    module_paths: list[str],
    provenance: str,
) -> None:
    for module_path in module_paths:
        _link_contract_dependency_module(snapshot, context, module_path, provenance)
