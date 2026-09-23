"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg.mapping_io import _mapping_section
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _configured_duplication_families,
)

__all__ = [
    "_duplication_analysis_config",
]


def _duplication_analysis_config(
    memory_mapping: dict[str, object],
) -> dict[str, object]:
    payload = _mapping_section(memory_mapping, "duplication_analysis")
    families = _configured_duplication_families(payload.get("families", {}))
    return {
        "enabled": bool(payload.get("enabled", True)),
        "min_cluster_size": _coerce_int(payload.get("min_cluster_size", 2), 2),
        "min_ast_nodes": _coerce_int(payload.get("min_ast_nodes", 12), 12),
        "families": tuple(families),
    }
