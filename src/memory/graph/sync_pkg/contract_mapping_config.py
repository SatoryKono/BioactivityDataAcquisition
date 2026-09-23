"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ContractMappingConfig
from memory.graph.sync_pkg.contract_mapping_values import _contract_mapping_values
from memory.graph.sync_pkg.contract_source_prefixes import _contract_source_prefixes
from memory.graph.sync_pkg.mapping_io import _mapping_dict_or_empty

__all__ = [
    "_contract_mapping_config",
]


def _contract_mapping_config(
    memory_mapping: dict[str, object],
) -> ContractMappingConfig:
    contracts_mapping = _mapping_dict_or_empty(memory_mapping.get("contracts"))
    return ContractMappingConfig(
        source_prefixes=_contract_source_prefixes(contracts_mapping),
        control_plane_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_modules"
        ),
        control_plane_runtime_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_runtime_modules"
        ),
        lineage_modules=_contract_mapping_values(contracts_mapping, "lineage_modules"),
        lineage_runtime_modules=_contract_mapping_values(
            contracts_mapping, "lineage_runtime_modules"
        ),
        control_plane_docs=_contract_mapping_values(
            contracts_mapping, "control_plane_docs"
        ),
        lineage_docs=_contract_mapping_values(contracts_mapping, "lineage_docs"),
        control_plane_anchor_fields=_contract_mapping_values(
            contracts_mapping, "control_plane_anchor_fields"
        ),
        lineage_anchor_fields=_contract_mapping_values(
            contracts_mapping, "lineage_anchor_fields"
        ),
    )
