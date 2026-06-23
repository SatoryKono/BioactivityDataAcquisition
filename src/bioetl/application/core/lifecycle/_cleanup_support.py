"""Private helpers for cleanup preview payload shaping."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

LayerInfoParts = tuple[str, int, bool]


def parse_layer_info_parts(info_dict: JsonDict) -> LayerInfoParts:
    """Parse one medallion-layer preview payload into primitive parts."""
    return (
        info_dict.get("path", ""),
        info_dict.get("file_count", 0),
        info_dict.get("exists", False),
    )


def parse_cleanup_preview_parts(
    preview_dict: JsonDict,
) -> tuple[LayerInfoParts, LayerInfoParts | None, int]:
    """Return primitive preview components without constructing service dataclasses."""
    silver_info = parse_layer_info_parts(preview_dict.get("silver", {}))
    gold_info = None
    if preview_dict.get("gold"):
        gold_info = parse_layer_info_parts(preview_dict["gold"])
    return silver_info, gold_info, preview_dict.get("total_files", 0)
