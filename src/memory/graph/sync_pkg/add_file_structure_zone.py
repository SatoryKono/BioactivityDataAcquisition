"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_mapping
from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_field_validation_item import (
    _merge_field_validation_item,
    _merge_key_nullability_item,
)
from memory.graph.sync_pkg.repo_zone_for_path import _add_repo_zone_file_structure

__all__ = [
    "_add_file_structure_zone",
    "_field_quality_index",
]


def _add_file_structure_zone(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
    _add_repo_zone_file_structure(
        snapshot,
        root,
        project,
        today,
        zone_name,
        relative_roots,
        config,
    )


def _field_quality_index(payload: dict[str, object]) -> dict[str, dict[str, JsonValue]]:
    quality_payload = _as_mapping(payload.get("quality"))
    index: dict[str, dict[str, JsonValue]] = {}
    field_validations = quality_payload.get("entity_field_validations")
    if isinstance(field_validations, list):
        for item in field_validations:
            _merge_field_validation_item(index, item)
    key_nullability = quality_payload.get("key_nullability")
    if isinstance(key_nullability, list):
        for item in key_nullability:
            _merge_key_nullability_item(index, item)
    return index
