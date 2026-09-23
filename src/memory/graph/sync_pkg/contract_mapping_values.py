"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_string_list
from memory.graph.sync_pkg.contract_policy_config_path import (
    _add_contract_policy_artifact,
    _contract_policy_config_path,
    _contract_policy_fields,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _contract_source_resolved_path,
    _link_contract_imported_modules,
    _link_contract_source_module,
    _update_contract_schema_classes,
)
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_contract_policy_config",
    "_contract_mapping_values",
    "_link_contract_source_dependencies",
]


def _contract_mapping_values(
    contracts_mapping: dict[str, object],
    key: str,
) -> list[str]:
    return _as_string_list(contracts_mapping.get(key))


def _link_contract_source_dependencies(
    snapshot: GraphSnapshot,
    context: ContractEntryContext,
    source_prefixes: tuple[str, ...],
) -> None:
    resolved = _contract_source_resolved_path(context)
    if resolved is None:
        return
    _link_contract_source_module(snapshot, context, resolved)
    _link_contract_imported_modules(snapshot, context, resolved, source_prefixes)
    _update_contract_schema_classes(snapshot, context, resolved)


def _add_contract_policy_config(
    snapshot: GraphSnapshot, context: ContractEntryContext
) -> None:
    contract_config_path = _contract_policy_config_path(context)
    if not contract_config_path.is_file():
        return
    contract_config = _read_yaml(contract_config_path)
    snapshot.add_node(
        "contract_surface",
        context.contract_ref,
        **_contract_policy_fields(contract_config),
    )
    artifact = _add_contract_policy_artifact(
        snapshot,
        context=context,
        contract_config_path=contract_config_path,
    )
    snapshot.add_relation(
        context.contract, "BACKED_BY", artifact, provenance="impact_contracts"
    )
