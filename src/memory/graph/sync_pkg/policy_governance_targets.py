"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable
from memory.graph.sync_pkg._core_models import NodeKey

__all__ = [
    "_policy_governance_targets",
]


def _policy_governance_targets(
    policy_payload: dict[str, object],
) -> tuple[NodeKey, ...]:
    targets: list[NodeKey] = []
    targets.extend(
        NodeKey("layer_family", str(name))
        for name in _as_iterable(policy_payload.get("governs_layers"))
    )
    targets.extend(
        NodeKey("quality_gate", str(name))
        for name in _as_iterable(policy_payload.get("governs_quality_gates"))
    )
    targets.extend(
        NodeKey("test_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_test_surfaces"))
    )
    targets.extend(
        NodeKey("doc_source_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_docs"))
    )
    return tuple(targets)
