"""Leaf helpers for nested mapping lookups without diagnostics facade imports."""

from __future__ import annotations

from collections.abc import Mapping


def lookup_mapping_path(
    mapping: Mapping[str, object],
    *path: str,
) -> object | None:
    """Read one nested mapping path using only mapping-shaped objects."""
    current: object = mapping
    for component in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(component)
    return current


__all__ = ["lookup_mapping_path"]
