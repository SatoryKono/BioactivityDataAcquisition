"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ContractMappingConfig

__all__ = [
    "_contract_dependency_doc_specs",
    "_contract_dependency_module_specs",
]


def _contract_dependency_module_specs(
    mapping_config: ContractMappingConfig,
) -> tuple[tuple[list[str], str], ...]:
    return (
        (mapping_config.control_plane_modules, "impact_contracts_control_plane"),
        (mapping_config.control_plane_runtime_modules, "impact_contracts_runtime"),
        (mapping_config.lineage_modules, "impact_contracts_lineage"),
        (mapping_config.lineage_runtime_modules, "impact_contracts_lineage_runtime"),
    )


def _contract_dependency_doc_specs(
    mapping_config: ContractMappingConfig,
) -> tuple[tuple[list[str], list[str], str, str, str], ...]:
    return (
        (
            mapping_config.control_plane_docs,
            mapping_config.control_plane_anchor_fields,
            "Control-plane contract reference for `{contract_ref}`.",
            "control_plane_contract_doc",
            "impact_contracts_control_plane",
        ),
        (
            mapping_config.lineage_docs,
            mapping_config.lineage_anchor_fields,
            "Lineage/traceability contract reference for `{contract_ref}`.",
            "lineage_contract_doc",
            "impact_contracts_lineage",
        ),
    )
