"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    load_contract_registry_payload,
)
from memory.graph.sync_pkg._core_models import ContractMappingConfig
from memory.graph.sync_pkg.contract_mapping_values import (
    _add_contract_policy_config,
    _link_contract_source_dependencies,
)
from memory.graph.sync_pkg.contract_source_prefixes import (
    _add_published_contract_artifacts,
)
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_contract_dependency_modules import (
    _link_contract_dependency_docs,
    _link_contract_dependency_modules,
)

__all__ = [
    "_contract_registry_payload",
    "_link_contract_dependencies",
]


def _contract_registry_payload(root: Path) -> dict[object, object]:
    payload = load_contract_registry_payload(root / DEFAULT_CONTRACT_REGISTRY_PATH)
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else {}


def _link_contract_dependencies(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    _link_contract_source_dependencies(
        snapshot, entry_context, mapping_config.source_prefixes
    )
    _add_contract_policy_config(snapshot, entry_context)
    _add_published_contract_artifacts(snapshot, entry_context)
    _link_contract_dependency_modules(snapshot, entry_context, mapping_config)
    _link_contract_dependency_docs(snapshot, entry_context, mapping_config)
