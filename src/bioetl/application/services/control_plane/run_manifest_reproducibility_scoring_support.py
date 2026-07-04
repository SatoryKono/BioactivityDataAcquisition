"""Shared utility helpers for reproducibility audit scoring."""

from __future__ import annotations


def bounded(score: int) -> int:
    return max(0, min(10, score))


def string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item is not None)


def supported_boundary_block_reason(lineage_boundary: object) -> str:
    if isinstance(lineage_boundary, dict) and lineage_boundary.get("reason"):
        return str(lineage_boundary.get("reason"))
    return "blocked_outside_supported_boundary"
