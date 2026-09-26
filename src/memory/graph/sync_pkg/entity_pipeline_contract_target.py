"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_string_list
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contract_ref_identity import _contract_ref_identity

__all__ = [
    "_entity_pipeline_contract_target",
]


def _entity_pipeline_contract_target(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    contract_ref: object,
    raw_tests: object,
) -> tuple[NodeKey, tuple[str, ...]] | None:
    contract_identity = _contract_ref_identity(contract_ref)
    if contract_identity is None:
        return None
    pipeline_key = entity_pipeline_index.get(contract_identity)
    if pipeline_key is None:
        return None
    test_paths = tuple(_as_string_list(raw_tests))
    if not test_paths:
        return None
    return pipeline_key, test_paths
