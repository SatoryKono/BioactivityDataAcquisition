"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_normalization_registry_module",
    "_normalization_evidence_update_payload",
]


def _normalization_evidence_update_payload(
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    module_path = evidence.get("normalization_profile_module_path")
    return {
        "normalization_profile_registered": bool(
            evidence.get("normalization_profile_registered", False)
        ),
        "normalization_profile_module_path": (
            str(module_path) if isinstance(module_path, str) and module_path else None
        ),
        "profile_field_count": _coerce_int(evidence.get("profile_field_count", 0), 0),
        "fallback_field_count": _coerce_int(evidence.get("fallback_field_count", 0), 0),
        "fallback_business_field_count": _coerce_int(
            evidence.get("fallback_business_field_count", 0), 0
        ),
        "fallback_technical_passthrough_field_count": _coerce_int(
            evidence.get("fallback_technical_passthrough_field_count", 0), 0
        ),
    }


def _link_normalization_registry_module(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    entity_key: NodeKey,
    module_path: JsonValue,
) -> None:
    if not isinstance(module_path, str) or not module_path:
        return
    module_key = NodeKey("module_surface", module_path)
    if module_key not in snapshot.nodes:
        return
    snapshot.add_relation(
        pipeline, "DEPENDS_ON", module_key, provenance="normalization_registry"
    )
    if entity_key in snapshot.nodes:
        snapshot.add_relation(
            entity_key, "DEPENDS_ON", module_key, provenance="normalization_registry"
        )
