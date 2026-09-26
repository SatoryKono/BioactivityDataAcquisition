"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.entity_pipeline_contract_target import (
    _entity_pipeline_contract_target,
)

__all__ = [
    "_entity_pipeline_contract_tests",
]


def _entity_pipeline_contract_tests(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> tuple[tuple[NodeKey, tuple[str, ...]], ...]:
    return tuple(
        target
        for contract_ref, raw_tests in ownership.items()
        for target in [
            _entity_pipeline_contract_target(
                entity_pipeline_index, contract_ref, raw_tests
            )
        ]
        if target is not None
    )
