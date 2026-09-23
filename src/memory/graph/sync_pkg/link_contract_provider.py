"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import CONTRACT_REGISTRY_RELATIVE_PATH
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_contract_registry_artifact",
    "_link_contract_provider",
]


def _link_contract_provider(
    snapshot: GraphSnapshot,
    contract_ref: str,
    contract: NodeKey,
) -> None:
    provider_name = contract_ref.split(".", 1)[0]
    provider_key = NodeKey("provider_surface", provider_name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            provider_key, "DEFINES", contract, provenance="impact_contracts"
        )


def _add_contract_registry_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
) -> NodeKey | None:
    registry_path = root / CONTRACT_REGISTRY_RELATIVE_PATH
    if not registry_path.is_file():
        return None
    relative_path = _rel_path(root, registry_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary="Contract registry for published data contracts.",
        source_path=relative_path,
        source_kind="contract_registry",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
