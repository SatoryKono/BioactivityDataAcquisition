"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.contract_mapping_values import _contract_mapping_values
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.published_contract_artifact_paths import (
    _published_contract_artifact_key,
    _published_contract_artifact_paths,
)

__all__ = [
    "_add_published_contract_artifacts",
    "_contract_source_prefixes",
]


def _contract_source_prefixes(contracts_mapping: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        _contract_mapping_values(contracts_mapping, "registry_source_prefixes")
        or [
            "bioetl.domain.contracts.gold",
            "bioetl.domain.schemas",
        ]
    )


def _add_published_contract_artifacts(
    snapshot: GraphSnapshot, context: ContractEntryContext
) -> None:
    for published_path in _published_contract_artifact_paths(context):
        artifact = _published_contract_artifact_key(snapshot, context, published_path)
        if artifact is None:
            continue
        snapshot.add_relation(
            context.contract, "BACKED_BY", artifact, provenance="impact_contracts"
        )
