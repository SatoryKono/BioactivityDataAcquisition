"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ContractMappingConfig
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _link_contract_doc_dependencies,
)
from memory.graph.sync_pkg.contract_dependency_module_specs import (
    _contract_dependency_doc_specs,
    _contract_dependency_module_specs,
)
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.published_contract_artifact_paths import (
    _link_contract_module_dependencies,
)

__all__ = [
    "_link_contract_dependency_docs",
    "_link_contract_dependency_modules",
]


def _link_contract_dependency_modules(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    for module_paths, provenance in _contract_dependency_module_specs(mapping_config):
        _link_contract_module_dependencies(
            snapshot,
            entry_context,
            module_paths,
            provenance,
        )


def _link_contract_dependency_docs(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    for (
        doc_paths,
        anchor_fields,
        summary,
        source_kind,
        provenance,
    ) in _contract_dependency_doc_specs(mapping_config):
        _link_contract_doc_dependencies(
            snapshot,
            entry_context,
            doc_paths,
            anchor_fields,
            summary=summary,
            source_kind=source_kind,
            provenance=provenance,
        )
